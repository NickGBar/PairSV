#!/usr/bin/env python3
"""HG002 gate-2 (SECONDARY/sensitivity, NIST SV v0.6 GRCh37): single-pass
Truvari matching against the mature, GRCh37-native NIST SV v0.6 Tier1
benchmark, with the same benchmark-region rule structure as the v5.0q
primary pass (manta_poc/hg002_gate2_pipeline.py), applied to v0.6's Tier1
confident-region BED instead.

This is a SEPARATE pipeline pass, run against a GRCh37-aligned HG002 BAM
(HG002.hs37d5.60x.1.bam) and a GRCh37-compatible reference (hs37d5.fa or its
BAM-exact subset, whichever run_manta_hg002_hs37d5.sbatch selected). Results
from this pass are NEVER pooled or averaged with the v5.0q primary result --
per EXTERNAL_EVAL_PROTOCOL_FROZEN.md ADDENDUM section 10 and the mission's
explicit "never pool" rule.

Truth labeling (v0.6's own recommended scheme, README point 1): "the calls
with PASS in the FILTER field are our highest confidence set of SVs >=50bp"
-- filtered to SVTYPE=DEL, |SVLEN|>=50, FILTER=PASS exactly, unlike v5.0q's
combined-VCF "." /HET1/HET2 scheme (v0.6's Tier1 VCF is not a combined
smvar+stvar file, so no such distinction is needed).

Truvari parameters: this project's own FROZEN params (identical to every
other Truvari pass in this project, section 2/3 of the frozen protocol),
NOT the v0.6 README's own suggested `-r 2000` default -- per the mission's
rule 6 ("same... metric definitions" across v5.0q and v0.6), consistency
with the rest of this project takes precedence over the source README's own
suggestion. This choice is documented here, not silently substituted.

Labeling:
  - tp-comp (Manta PASS DEL matched to a v0.6 Tier1 PASS truth deletion) -> Positive
  - fp AND both breakpoints inside HG002_SVs_Tier1_v0.6.bed -> Known negative
  - EITHER breakpoint outside/crossing the Tier1 BED -> Unknown/excluded,
    never folded into Known negative or treated as a false positive.

Usage: python3 hg002_v0.6_gate2_pipeline.py
"""
from __future__ import annotations

import bisect
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import pysam

BASE = Path("/scratch/igorno-deepsv_poc")
GIAB = BASE / "giab_hg002"
REF = BASE / "reference/hs37d5.fa"  # overridden below if a subset reference was used for Manta
WD = BASE / "hg002_v0.6_external"
WD.mkdir(parents=True, exist_ok=True)

TRUTH_VCF = GIAB / "HG002_SVs_Tier1_v0.6.vcf.gz"
BENCHMARK_BED = GIAB / "HG002_SVs_Tier1_v0.6.bed"
MANTA_DIPLOID_VCF = BASE / "results/HG002_hs37d5_wgs/results/variants/diploidSV.vcf.gz"
MANTA_EXIT_CODE_FILE = BASE / "results/HG002_hs37d5_wgs_exit_code.txt"

BGZIP = "/home/igorno/miniconda3/envs/bioinfo/bin/bgzip"
TABIX = "/home/igorno/miniconda3/envs/bioinfo/bin/tabix"
TRUVARI = "/home/igorno/miniconda3/envs/truvari_env/bin/truvari"

# Frozen project-wide params (EXTERNAL_EVAL_PROTOCOL_FROZEN.md section 2/3),
# used identically for v5.0q and v0.6 -- NOT the v0.6 README's own -r 2000 suggestion.
TRUVARI_PARAMS = [
    "--sizemin", "50", "--sizefilt", "30", "--sizemax", "50000",
    "--refdist", "500", "--pctseq", "0.7", "--pctsize", "0.7", "--pctovl", "0.0",
    "--pick", "single",
]


def resolve_manta_reference() -> Path:
    """The Manta run script auto-selects either the full hs37d5 reference or
    a BAM-exact subset reference, recorded in the exit-code file. Reuse
    whichever it used, for consistency with what Manta actually called
    against."""
    if not MANTA_EXIT_CODE_FILE.exists():
        raise SystemExit(f"Manta exit-code file not found: {MANTA_EXIT_CODE_FILE} -- run Manta first")
    for line in MANTA_EXIT_CODE_FILE.read_text().splitlines():
        if line.startswith("REFERENCE_USED="):
            return Path(line.split("=", 1)[1])
    raise SystemExit("REFERENCE_USED not recorded in Manta exit-code file")


def load_benchmark_bed(path: Path) -> dict[str, tuple[list[int], list[int]]]:
    by_chrom: dict[str, list[tuple[int, int]]] = defaultdict(list)
    with open(path) as f:
        for line in f:
            if not line.strip() or line.startswith("#") or line.startswith("track"):
                continue
            parts = line.split("\t")
            chrom, start, end = parts[0], parts[1], parts[2]
            by_chrom[chrom].append((int(start), int(end)))
    out = {}
    for chrom, intervals in by_chrom.items():
        intervals.sort()
        out[chrom] = ([s for s, _ in intervals], [e for _, e in intervals])
    return out


def point_in_bed(bed: dict, chrom: str, pos: int) -> bool:
    if chrom not in bed:
        return False
    starts, ends = bed[chrom]
    i = bisect.bisect_right(starts, pos) - 1
    if i < 0:
        return False
    return starts[i] <= pos < ends[i]


def both_breakpoints_in_bed(bed: dict, chrom: str, start0: int, end0: int) -> bool:
    return point_in_bed(bed, chrom, start0) and point_in_bed(bed, chrom, max(start0, end0 - 1))


def extract_truth_del_ge50() -> Path:
    """v0.6 Tier1: FILTER=PASS, SVTYPE=DEL, |SVLEN|>=50 -- the README's own
    definition of the highest-confidence SV set."""
    out_path = WD / "HG002_v0.6_truth_DEL_ge50.vcf"
    vf = pysam.VariantFile(str(TRUTH_VCF))
    out = pysam.VariantFile(str(out_path), "w", header=vf.header)
    n_total = n_kept = 0
    for rec in vf:
        n_total += 1
        values = list(rec.filter.keys())
        is_pass = values == ["PASS"] or set(values) == {"PASS"}
        if not is_pass:
            continue
        if rec.info.get("SVTYPE") != "DEL":
            continue
        svlen = rec.info.get("SVLEN")
        if isinstance(svlen, tuple):
            svlen = svlen[0] if svlen else None
        if svlen is None or abs(int(svlen)) < 50:
            continue
        out.write(rec)
        n_kept += 1
    out.close()
    vf.close()
    print(f"HG002 v0.6 truth: {n_kept}/{n_total} PASS DEL>=50bp records written to {out_path}", flush=True)
    return out_path


def extract_manta_pass_del() -> Path:
    vf = pysam.VariantFile(str(MANTA_DIPLOID_VCF))
    out_path = WD / "HG002_hs37d5_manta_PASS_DEL.vcf"
    out = pysam.VariantFile(str(out_path), "w", header=vf.header)
    n_total = n_kept = 0
    for rec in vf:
        n_total += 1
        values = list(rec.filter.keys())
        is_pass = (not values) or values == ["PASS"] or set(values) == {"PASS"}
        if not is_pass:
            continue
        if rec.info.get("SVTYPE") != "DEL":
            continue
        out.write(rec)
        n_kept += 1
    out.close()
    vf.close()
    print(f"HG002 hs37d5 Manta: {n_kept}/{n_total} PASS DEL records", flush=True)
    return out_path


def bgzip_tabix(path: Path) -> Path:
    gz_path = Path(str(path) + ".gz")
    subprocess.run([BGZIP, "-f", str(path)], check=True)
    subprocess.run([TABIX, "-p", "vcf", str(gz_path)], check=True)
    return gz_path


def manta_interval(rec):
    end = rec.info.get("END")
    if end is not None:
        return rec.pos - 1, int(end)
    svlen = rec.info.get("SVLEN")
    if isinstance(svlen, tuple):
        svlen = svlen[0] if svlen else None
    if svlen is not None:
        return rec.pos - 1, rec.pos - 1 + abs(int(svlen))
    return None


def key(rec):
    return (rec.chrom, rec.pos, rec.ref, rec.alts)


def main():
    print("=== HG002 gate2 SECONDARY: NIST SV v0.6 GRCh37 single-pass Truvari matching ===", flush=True)
    manta_ref = resolve_manta_reference()
    print(f"Using reference (matching what Manta actually called against): {manta_ref}", flush=True)

    truth_del = extract_truth_del_ge50()
    truth_del_gz = bgzip_tabix(truth_del)

    manta_pass_del = extract_manta_pass_del()
    manta_pass_del_gz = bgzip_tabix(manta_pass_del)

    outdir = WD / "truvari_v0.6_secondary"
    if outdir.exists():
        subprocess.run(["rm", "-rf", str(outdir)], check=True)
    cmd = [TRUVARI, "bench", "-b", str(truth_del_gz), "-c", str(manta_pass_del_gz),
           "-f", str(manta_ref), "-o", str(outdir), "--includebed", str(BENCHMARK_BED), *TRUVARI_PARAMS]
    print("RUN:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

    print("=== benchmark-region rule: independent both-breakpoints-in-BED check ===", flush=True)
    bed = load_benchmark_bed(BENCHMARK_BED)

    positive_ids = set()
    for rec in pysam.VariantFile(str(outdir / "tp-comp.vcf.gz")):
        positive_ids.add(key(rec))

    all_manta = {}
    for i, rec in enumerate(pysam.VariantFile(str(manta_pass_del_gz))):
        interval = manta_interval(rec)
        in_bed = both_breakpoints_in_bed(bed, rec.chrom, *interval) if interval else False
        all_manta[key(rec)] = {"chrom": rec.chrom, "pos": rec.pos, "interval": interval,
                                "in_bed": in_bed, "manta_id": rec.id, "index": i}

    classified = {}
    for k, meta in all_manta.items():
        if not meta["in_bed"]:
            classified[k] = "excluded_outside_or_crossing_benchmark_bed"
        elif k in positive_ids:
            classified[k] = "positive"
        else:
            classified[k] = "known_negative"

    class_counts = Counter(classified.values())
    report = {
        "sample": "HG002", "truth_source": "NIST SV v0.6 GRCh37 Tier1 (SECONDARY/sensitivity, mature but incomplete)",
        "reference_build": "GRCh37/hs37d5", "pooled_with_v5.0q": False,
        "total_manta_pass_del": len(all_manta),
        "class_counts": dict(class_counts),
        "sanity_sum_check": sum(class_counts.values()) == len(all_manta),
        "truvari_params_used": "project-frozen params (refdist=500), NOT the v0.6 README's own suggested -r 2000 -- documented consistency choice",
    }
    with open(WD / "hg002_v0.6_gate2_classification_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2), flush=True)

    by_manta_id = {meta["manta_id"]: classified[k] for k, meta in all_manta.items()}
    with open(WD / "hg002_v0.6_classification_by_manta_id.json", "w") as f:
        json.dump(by_manta_id, f, indent=2)

    print("DONE: HG002 v0.6 gate2 (secondary/sensitivity)", flush=True)


if __name__ == "__main__":
    main()

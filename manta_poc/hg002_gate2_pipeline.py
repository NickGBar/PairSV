#!/usr/bin/env python3
"""HG002 gate-2 (external, v5.0q primary truth source): single-pass Truvari
matching against the GIAB v5.0q GRCh38 assembly-based structural-variant
benchmark, with the benchmark-region rule from
manta_poc/EXTERNAL_EVAL_PROTOCOL_FROZEN.md ADDENDUM sections 9-10.

Unlike the 5-person POC's two-pass PanGenie carrier/reference-truth design
(gate2_pipeline.py), v5.0q supplies ONE truth VCF + ONE confident-region BED
-- the standard GIAB design. Labeling:
  - tp-comp (Manta PASS DEL matched to a v5.0q truth deletion) -> Positive
  - fp AND both breakpoints inside the benchmark BED -> Known negative
  - EITHER breakpoint outside/crossing the BED (regardless of Truvari's own
    tp/fp call) -> Unknown/excluded, its own bucket, NEVER folded into
    Known negative or treated as a false positive.

Frozen Truvari params (identical to every other gate-2 pass this project has
run): --refdist 500 --pctseq 0.7 --pctsize 0.7 --pctovl 0.0 --sizemin 50
--sizefilt 30 --sizemax 50000 --pick single. Original Manta coordinates are
never touched by truth coordinates at any point.

Usage: python3 hg002_gate2_pipeline.py
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
GIAB = BASE / "giab_hg002"  # truth VCF/BED live here (already downloaded+verified this session)
REF = BASE / "reference/GRCh38_full.fa"
WD = BASE / "hg002_external"
WD.mkdir(parents=True, exist_ok=True)

TRUTH_VCF = GIAB / "HG002_GRCh38_v5.0q_stvar.vcf.gz"
BENCHMARK_BED = GIAB / "HG002_GRCh38_v5.0q_stvar.benchmark.bed"
MANTA_DIPLOID_VCF = BASE / "results/HG002_wgs/results/variants/diploidSV.vcf.gz"

BGZIP = "/home/igorno/miniconda3/envs/bioinfo/bin/bgzip"
TABIX = "/home/igorno/miniconda3/envs/bioinfo/bin/tabix"
TRUVARI = "/home/igorno/miniconda3/envs/truvari_env/bin/truvari"

TRUVARI_PARAMS = [
    "--sizemin", "50", "--sizefilt", "30", "--sizemax", "50000",
    "--refdist", "500", "--pctseq", "0.7", "--pctsize", "0.7", "--pctovl", "0.0",
    "--pick", "single",
]

SVTYPE_RE = re.compile(r"SVTYPE=([A-Z]+)")
SVLEN_RE = re.compile(r"SVLEN=(-?[0-9]+)")
USABLE_FILTERS = {".", "HET1", "HET2", "HET1;HET2"}  # excludes GAP1/GAP2-flagged records


def load_benchmark_bed(path: Path) -> dict[str, tuple[list[int], list[int]]]:
    """chrom -> (sorted starts, sorted ends) for O(log n) point-in-interval
    containment checks via bisect. Assumes non-overlapping, sorted-by-start
    BED intervals (standard for a GIAB confident-region BED)."""
    by_chrom: dict[str, list[tuple[int, int]]] = defaultdict(list)
    with open(path) as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            chrom, start, end = line.split("\t")[:3]
            by_chrom[chrom].append((int(start), int(end)))
    out = {}
    for chrom, intervals in by_chrom.items():
        intervals.sort()
        starts = [s for s, _ in intervals]
        ends = [e for _, e in intervals]
        out[chrom] = (starts, ends)
    return out


def point_in_bed(bed: dict, chrom: str, pos: int) -> bool:
    """0-based half-open point containment check."""
    if chrom not in bed:
        return False
    starts, ends = bed[chrom]
    i = bisect.bisect_right(starts, pos) - 1
    if i < 0:
        return False
    return starts[i] <= pos < ends[i]


def both_breakpoints_in_bed(bed: dict, chrom: str, start0: int, end0: int) -> bool:
    """Section 9: candidate included only if BOTH deletion breakpoints fall
    inside the benchmark BED. start0/end0 are 0-based; the deletion's two
    breakpoints are its start and its end-1 (last deleted base)."""
    return point_in_bed(bed, chrom, start0) and point_in_bed(bed, chrom, max(start0, end0 - 1))


def extract_truth_del_ge50(sample: str = "HG002") -> Path:
    """Filter v5.0q's combined smvar+stvar VCF to usable (non-GAP-flagged)
    DEL records with |SVLEN|>=50, for use as the Truvari base VCF."""
    out_path = WD / "HG002_v5.0q_truth_DEL_ge50.vcf"
    vf = pysam.VariantFile(str(TRUTH_VCF))
    header = vf.header
    if sample not in header.samples:
        # v5.0q truth VCFs may be single-sample or genotype-less; if the sample
        # column differs, use the first (and typically only) sample.
        sample = list(header.samples)[0] if len(header.samples) else None
    out = pysam.VariantFile(str(out_path), "w", header=header)
    n_total = n_kept = 0
    for rec in vf:
        n_total += 1
        # pysam represents FILTER='.' as an empty filter-keys set.
        filt_values = set(rec.filter.keys()) if rec.filter.keys() else {"."}
        if not (filt_values & USABLE_FILTERS):
            continue
        svtype = rec.info.get("SVTYPE")
        if svtype != "DEL":
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
    print(f"HG002 truth: {n_kept}/{n_total} usable DEL>=50bp records written to {out_path}", flush=True)
    return out_path


def extract_manta_pass_del() -> Path:
    vf = pysam.VariantFile(str(MANTA_DIPLOID_VCF))
    header = vf.header
    out_path = WD / "HG002_manta_PASS_DEL.vcf"
    out = pysam.VariantFile(str(out_path), "w", header=header)
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
    print(f"HG002 Manta: {n_kept}/{n_total} PASS DEL records", flush=True)
    return out_path


def bgzip_tabix(path: Path) -> Path:
    gz_path = Path(str(path) + ".gz")
    subprocess.run([BGZIP, "-f", str(path)], check=True)
    subprocess.run([TABIX, "-p", "vcf", str(gz_path)], check=True)
    return gz_path


def manta_interval(rec):
    end = rec.info.get("END")
    if end is not None:
        return rec.pos - 1, int(end)  # 0-based start, 0-based-exclusive end
    svlen = rec.info.get("SVLEN")
    if isinstance(svlen, tuple):
        svlen = svlen[0] if svlen else None
    if svlen is not None:
        return rec.pos - 1, rec.pos - 1 + abs(int(svlen))
    return None


def key(rec):
    return (rec.chrom, rec.pos, rec.ref, rec.alts)


def main():
    print("=== HG002 gate2: v5.0q single-pass Truvari matching ===", flush=True)
    truth_del = extract_truth_del_ge50()
    truth_del_gz = bgzip_tabix(truth_del)

    manta_pass_del = extract_manta_pass_del()
    manta_pass_del_gz = bgzip_tabix(manta_pass_del)

    outdir = WD / "truvari_v5.0q_primary"
    if outdir.exists():
        subprocess.run(["rm", "-rf", str(outdir)], check=True)
    cmd = [TRUVARI, "bench", "-b", str(truth_del_gz), "-c", str(manta_pass_del_gz),
           "-f", str(REF), "-o", str(outdir), "--includebed", str(BENCHMARK_BED), *TRUVARI_PARAMS]
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
        "sample": "HG002", "truth_source": "GIAB v5.0q GRCh38 stvar (primary, Draft)",
        "total_manta_pass_del": len(all_manta),
        "class_counts": dict(class_counts),
        "sanity_sum_check": sum(class_counts.values()) == len(all_manta),
    }
    with open(WD / "hg002_gate2_classification_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2), flush=True)

    # store classification keyed by manta_id for the manifest-building step
    by_manta_id = {meta["manta_id"]: classified[k] for k, meta in all_manta.items()}
    with open(WD / "hg002_classification_by_manta_id.json", "w") as f:
        json.dump(by_manta_id, f, indent=2)

    print("DONE: HG002 gate2", flush=True)


if __name__ == "__main__":
    main()

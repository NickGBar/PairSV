#!/usr/bin/env python3
"""HG002 v0.6 (SECONDARY/sensitivity, GRCh37) gate-3 manifest + BAM
extraction. Mirrors hg002_gate3_manifest_and_extract.py exactly, adapted for
the hs37d5 (GRCh37) BAM and the v0.6 classification. Original Manta
coordinates only. Excluded/boundary candidates (outside or crossing the
Tier1 benchmark BED) are tracked but not extracted for scoring, matching the
v5.0q primary pass's convention.

Usage: python3 hg002_v0.6_gate3_manifest_and_extract.py
"""
from __future__ import annotations

import json
import time
import traceback
from collections import Counter

import h5py
import numpy as np
import pysam

import sys
sys.path.insert(0, "/scratch/igorno-deepsv_poc/pairsv_parity")
from deepsv.multisample.extraction import (
    Candidate, CandidateExtractionError, ExampleTensors, RemoteCramSession,
    build_candidate_refalt_tokens, extract_example_from_reads,
)
from deepsv.multisample.storage import PairSVShardWriter

from pathlib import Path

BASE = Path("/scratch/igorno-deepsv_poc")
WD = BASE / "hg002_v0.6_external"
BAM = BASE / "local_slices/HG002_hs37d5_full/HG002.hs37d5.60x.1.bam"


def resolve_manta_reference() -> Path:
    exit_code_file = BASE / "results/HG002_hs37d5_wgs_exit_code.txt"
    for line in exit_code_file.read_text().splitlines():
        if line.startswith("REFERENCE_USED="):
            return Path(line.split("=", 1)[1])
    raise SystemExit("REFERENCE_USED not recorded")


REF = resolve_manta_reference()


def svlen_of(rec):
    sl = rec.info.get("SVLEN")
    if isinstance(sl, tuple):
        sl = sl[0] if sl else None
    if sl is not None:
        return abs(int(sl))
    end = rec.info.get("END")
    return abs(int(end) - rec.pos) if end is not None else None


def manta_interval(rec):
    end = rec.info.get("END")
    if end is not None:
        return rec.pos, int(end)
    svlen = rec.info.get("SVLEN")
    if isinstance(svlen, tuple):
        svlen = svlen[0] if svlen else None
    if svlen is not None:
        return rec.pos, rec.pos + abs(int(svlen))
    return None


def build_manifest() -> str:
    by_manta_id = json.load(open(WD / "hg002_v0.6_classification_by_manta_id.json"))
    manta = pysam.VariantFile(str(WD / "HG002_hs37d5_manta_PASS_DEL.vcf.gz"))
    rows = []
    excluded_bed = 0
    for i, rec in enumerate(manta):
        cls = by_manta_id.get(rec.id)
        if cls is None:
            continue
        if cls == "excluded_outside_or_crossing_benchmark_bed":
            excluded_bed += 1
            continue
        label = 1 if cls == "positive" else 0
        interval = manta_interval(rec)
        gt = rec.samples[0].get("GT") if len(rec.samples) else None
        gt_str = "/".join(str(v) for v in gt) if gt and all(v is not None for v in gt) else None
        row = {
            "candidate_id": f"HG002v06_manta_{i:06d}", "manta_id": rec.id, "chrom": rec.chrom,
            "vcf_pos": rec.pos, "svlen_manta": svlen_of(rec), "manta_genotype": gt_str,
            "class": cls, "label": label,
        }
        if interval is None:
            row["extraction_precheck_status"] = "failed_uninterpretable_interval"
        else:
            del_start0, del_end0 = interval
            length = del_end0 - del_start0
            row["del_start0"], row["del_end0"], row["length"] = del_start0, del_end0, length
            if length > 10_000:
                row["extraction_precheck_status"] = "unsupported_length_gt_10000bp_predefined_exclusion"
            elif length < 50:
                row["extraction_precheck_status"] = "failed_length_below_50bp"
            else:
                row["extraction_precheck_status"] = "ok"
        rows.append(row)

    manifest_path = WD / "hg002_v0.6_gate3_candidate_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"HG002 v0.6: manifest rows={len(rows)} (+{excluded_bed} excluded by benchmark-region rule) "
          f"by_class={dict(Counter(r['class'] for r in rows))} "
          f"by_precheck={dict(Counter(r['extraction_precheck_status'] for r in rows))}", flush=True)
    return str(manifest_path)


def extract(manifest_path: str) -> str:
    manifest = json.load(open(manifest_path))
    eligible = [row for row in manifest if row["extraction_precheck_status"] == "ok"]
    print(f"HG002 v0.6: eligible candidates: {len(eligible)} / {len(manifest)}", flush=True)

    fasta = pysam.FastaFile(str(REF))

    def fetch_reference(chrom, start, end):
        return fasta.fetch(chrom, max(0, start), end)

    session = RemoteCramSession(str(BAM), str(BAM) + ".bai", str(REF), max_attempts=3, timeout_seconds=60)
    session.open()

    n = len(eligible)
    images = np.zeros((n, 2, 6, 64, 128), dtype=np.uint8)
    scalars = np.zeros((n, 17), dtype=np.float32)
    read_tokens = np.zeros((n, 2, 48, 128), dtype=np.uint8)
    read_mask = np.zeros((n, 2, 48), dtype=np.uint8)
    refalt_tokens = np.zeros((n, 2, 1024), dtype=np.uint8)
    success = np.zeros(n, dtype=bool)
    failure_reason = [""] * n
    candidate_ids = [row["candidate_id"] for row in eligible]

    started = time.monotonic()
    for i, row in enumerate(eligible):
        candidate = Candidate(candidate_id=row["candidate_id"], chrom=row["chrom"],
                               del_start0=row["del_start0"], del_end0=row["del_end0"], length=row["length"])
        try:
            left_reads, right_reads, _fetches, _elapsed = session.fetch_breakpoints(candidate)
            example = extract_example_from_reads(candidate, left_reads, right_reads, fetch_reference)
            tokens = build_candidate_refalt_tokens(candidate, fetch_reference)
            images[i], scalars[i] = example.images, example.scalars
            read_tokens[i], read_mask[i] = example.read_tokens, example.read_mask
            refalt_tokens[i] = tokens
            success[i] = True
        except CandidateExtractionError as exc:
            failure_reason[i] = f"CandidateExtractionError: {exc}"
        except Exception as exc:
            failure_reason[i] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}"

        if (i + 1) % 500 == 0 or (i + 1) == n:
            elapsed = time.monotonic() - started
            rate = (i + 1) / elapsed
            print(f"HG002 v0.6: [{i+1}/{n}] success={success[:i+1].sum()} elapsed={elapsed:.1f}s rate={rate:.2f}/s", flush=True)

    session.close()
    fasta.close()

    extracted_path = WD / "hg002_v0.6_gate3_extracted.h5"
    with h5py.File(extracted_path, "w") as h5:
        string = h5py.string_dtype("utf-8")
        h5.create_dataset("candidate_id", data=np.asarray(candidate_ids, dtype=object), dtype=string)
        h5.create_dataset("images", data=images, compression="gzip", compression_opts=1)
        h5.create_dataset("scalars", data=scalars)
        h5.create_dataset("read_tokens", data=read_tokens, compression="gzip", compression_opts=1)
        h5.create_dataset("read_mask", data=read_mask)
        h5.create_dataset("refalt_tokens", data=refalt_tokens, compression="gzip", compression_opts=1)
        h5.create_dataset("success", data=success)
        h5.create_dataset("failure_reason", data=np.asarray(failure_reason, dtype=object), dtype=string)

    print(f"HG002 v0.6: EXTRACT DONE. success={int(success.sum())}/{n} ({100*success.mean():.1f}%)", flush=True)
    print("HG002 v0.6: failure reasons:", dict(Counter(r.split(":")[0] for r in failure_reason if r)), flush=True)
    return str(extracted_path)


def convert_shard(extracted_path: str) -> str:
    with h5py.File(extracted_path, "r") as h5:
        success = h5["success"][:]
        idx = success.nonzero()[0]
        candidate_ids = [c.decode() if isinstance(c, bytes) else c for c in h5["candidate_id"][idx]]
        images = h5["images"][idx]
        scalars = h5["scalars"][idx]
        read_tokens = h5["read_tokens"][idx]
        read_mask = h5["read_mask"][idx]
        refalt_tokens = h5["refalt_tokens"][idx]

    n = len(candidate_ids)
    shard_path = str(WD / "pairsv_shard_HG002v06_gate3.h5")
    print(f"HG002 v0.6: packing {n} successful candidates into frozen shard schema", flush=True)
    with PairSVShardWriter(shard_path, n, shard_id=0) as writer:
        writer.write_candidates(candidate_ids, refalt_tokens, np.zeros((n, 2), dtype=np.int64))
        for i in range(n):
            tensors = ExampleTensors(
                images=images[i], read_tokens=read_tokens[i], read_mask=read_mask[i], scalars=scalars[i],
                read_cigar=np.full((2, 48), b"", dtype="S64"), read_strand=np.zeros((2, 48), dtype=np.int8),
                read_mapq=np.zeros((2, 48), dtype=np.uint8), read_mean_bq=np.zeros((2, 48), dtype=np.float32),
                read_supplementary=np.zeros((2, 48), dtype=np.uint8), read_name_hash=np.full((2, 48), b"", dtype="S16"),
                read_selection_reason=np.zeros((2, 48), dtype=np.uint8),
            )
            writer.write_success(i, {"row_id": candidate_ids[i], "sample_id": "HG002v06", "candidate_id": candidate_ids[i],
                                      "chrom": "", "label": 0, "del_start0": 0, "del_end0": 0}, tensors, candidate_index=i)
    print(f"HG002 v0.6: wrote {shard_path}", flush=True)
    return shard_path


def main():
    manifest_path = build_manifest()
    extracted_path = extract(manifest_path)
    convert_shard(extracted_path)
    print("DONE: HG002 v0.6 gate3 manifest+extract+shard", flush=True)


if __name__ == "__main__":
    main()

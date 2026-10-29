#!/usr/bin/env python3
"""Extract one independent PAIR-SV HDF5 shard from remote indexed CRAMs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pysam

from deepsv.multisample.extraction import (
    Candidate,
    CandidateExtractionError,
    RemoteCramSession,
    build_candidate_refalt_tokens,
    extract_example_from_reads,
)
from deepsv.multisample.qc import qc_shard, render_representative_pileups, save_qc_report
from deepsv.multisample.storage import PairSVShardWriter, write_checksums


REFERENCE_URL = (
    "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/"
    "GRCh38_reference_genome/GRCh38_full_analysis_set_plus_decoy_hla.fa"
)


def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {message}", flush=True)


def find_input_file(name: str, root: str) -> Path:
    matches = sorted(Path(root).rglob(name))
    if not matches:
        raise FileNotFoundError(f"{name} not found below {root}")
    # Prefer the strict v3 artifact if multiple historical kernel sources exist.
    strict = [path for path in matches if "manifest50-hq" in str(path) or "pairsv" in str(path)]
    return strict[0] if strict else matches[0]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def download_with_retries(url: str, path: Path, attempts: int = 3) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(attempts):
        try:
            with urlopen(url, timeout=600) as source, path.open("wb") as target:
                shutil.copyfileobj(source, target, length=1 << 20)
            if path.stat().st_size == 0:
                raise OSError("downloaded file is empty")
            return path.stat().st_size
        except Exception as exc:
            last_error = exc
            path.unlink(missing_ok=True)
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"download_failed:{url}:{last_error}")


def prepare_reference(path: Path) -> int:
    downloaded = 0
    if not path.exists() or not path.stat().st_size:
        downloaded += download_with_retries(REFERENCE_URL, path)
    fai = Path(str(path) + ".fai")
    if not fai.exists():
        try:
            downloaded += download_with_retries(REFERENCE_URL + ".fai", fai)
        except RuntimeError:
            pysam.faidx(str(path))
    fasta = pysam.FastaFile(str(path))
    required = {f"chr{index}" for index in range(1, 23)}
    if not required.issubset(fasta.references):
        raise RuntimeError("reference_mismatch:GRCh38 chr1-chr22 contigs are missing")
    fasta.close()
    return downloaded


def deterministic_subset(rows: list[dict[str, str]], per_class_per_sample: int | None) -> list[dict[str, str]]:
    if per_class_per_sample is None:
        return rows
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    by_candidate: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["sample"], row["label"])].append(row)
        by_candidate[row["candidate_id"]].append(row)
    selected: list[dict[str, str]] = []
    selected_ids = set()
    selected_candidates = set()
    counts = Counter()

    def random_key(value: str) -> str:
        return hashlib.sha256(f"pairsv-shard-subset-v2|{value}".encode()).hexdigest()

    def take_pair(predicate) -> bool:
        options = []
        for candidate_id, candidate_rows in by_candidate.items():
            if candidate_id in selected_candidates:
                continue
            positives = [row for row in candidate_rows if row["label"] == "1" and predicate(row)]
            negatives = [row for row in candidate_rows if row["label"] == "0"]
            for positive in positives:
                for negative in negatives:
                    if positive["sample"] == negative["sample"]:
                        continue
                    if counts[(positive["sample"], "1")] >= per_class_per_sample:
                        continue
                    if counts[(negative["sample"], "0")] >= per_class_per_sample:
                        continue
                    options.append((random_key(positive["row_id"] + negative["row_id"]), positive, negative))
        if not options:
            return False
        _, positive, negative = min(options, key=lambda item: item[0])
        for row in (positive, negative):
            selected.append(row)
            selected_ids.add(row["row_id"])
            counts[(row["sample"], row["label"])] += 1
        selected_candidates.add(positive["candidate_id"])
        return True

    # Guarantee literal representatives for the mandatory visual review,
    # while retaining cross-person same-candidate positive/negative pairs.
    representatives = (
        lambda row: 50 <= int(row["length"]) <= 200,
        lambda row: 200 < int(row["length"]) < 2_000,
        lambda row: int(row["length"]) >= 2_000,
        lambda row: row["genotype"] in {"0/1", "1/0"},
        lambda row: row["genotype"] == "1/1",
    )
    for predicate in representatives:
        if not take_pair(predicate):
            raise RuntimeError("deterministic subset lacks a mandatory representative category")

    # Fill remaining quotas in a stable pseudo-random candidate order. This
    # avoids the chromosome-prefix bias caused by lexicographic candidate IDs.
    for candidate_id in sorted(by_candidate, key=random_key):
        if candidate_id in selected_candidates:
            continue
        positives = sorted((row for row in by_candidate[candidate_id] if row["label"] == "1"), key=lambda row: row["row_id"])
        negatives = sorted((row for row in by_candidate[candidate_id] if row["label"] == "0"), key=lambda row: row["row_id"])
        pair = next(
            (
                (positive, negative)
                for positive in positives
                for negative in negatives
                if positive["sample"] != negative["sample"]
                and counts[(positive["sample"], "1")] < per_class_per_sample
                and counts[(negative["sample"], "0")] < per_class_per_sample
            ),
            None,
        )
        if pair is None:
            continue
        for row in pair:
            if row["row_id"] not in selected_ids:
                selected.append(row)
                selected_ids.add(row["row_id"])
                counts[(row["sample"], row["label"])] += 1
        selected_candidates.add(candidate_id)
    for key in sorted(grouped):
        values = sorted(grouped[key], key=lambda row: random_key(row["row_id"]))
        for row in values:
            if counts[key] >= per_class_per_sample:
                break
            if row["row_id"] in selected_ids:
                continue
            selected.append(row)
            selected_ids.add(row["row_id"])
            counts[key] += 1
    missing = {key: per_class_per_sample - counts[key] for key in grouped if counts[key] != per_class_per_sample}
    if missing:
        raise RuntimeError(f"deterministic subset could not fill requested quotas: {missing}")
    return sorted(selected, key=lambda row: (row["sample"], -int(row["label"]), row["row_id"]))


def validate_candidate_reference(row: dict[str, str], fasta: pysam.FastaFile) -> None:
    sequence = fasta.fetch(
        row["chrom"], int(row["ref_start0"]), int(row["ref_start0"]) + int(row["ref_length"])
    ).upper()
    observed = hashlib.sha256(sequence.encode()).hexdigest()
    if observed != row["ref_sha256"]:
        raise RuntimeError(
            f"reference_mismatch:{row['candidate_id']}:expected={row['ref_sha256']}:observed={observed}"
        )


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", type=int, required=True, choices=range(10))
    parser.add_argument("--input-root", default="/kaggle/input")
    parser.add_argument("--output-dir", default="/kaggle/working")
    parser.add_argument("--temp-dir", default="/kaggle/temp")
    parser.add_argument("--max-per-class-per-sample", type=int, default=None)
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()

    started_wall = time.time()
    output = Path(args.output_dir)
    temp = Path(args.temp_dir)
    output.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    manifest_path = find_input_file("sample_candidate_manifest.tsv", args.input_root)
    catalog_path = find_input_file("candidate_catalog.tsv", args.input_root)
    sample_path = find_input_file("sample_cram_manifest.tsv", args.input_root)
    manifest_rows = [row for row in read_tsv(manifest_path) if int(row["shard"]) == args.shard]
    manifest_rows = deterministic_subset(manifest_rows, args.max_per_class_per_sample)
    if not manifest_rows:
        raise RuntimeError(f"shard {args.shard} has no manifest rows")
    samples = {row["sample"]: row for row in read_tsv(sample_path) if int(row["shard"]) == args.shard}
    if set(row["sample"] for row in manifest_rows) != set(samples):
        raise RuntimeError("sample mapping and pair manifest disagree")
    catalog = {row["candidate_id"]: row for row in read_tsv(catalog_path)}
    missing_candidates = sorted(set(row["candidate_id"] for row in manifest_rows) - set(catalog))
    if missing_candidates:
        raise RuntimeError(f"candidate catalog missing {missing_candidates[:5]}")

    reference = temp / "GRCh38_full_analysis_set_plus_decoy_hla.fa"
    measured_bytes = prepare_reference(reference)
    fasta = pysam.FastaFile(str(reference))
    candidate_ids = sorted(set(row["candidate_id"] for row in manifest_rows))
    refalt_tokens = np.zeros((len(candidate_ids), 2, 1024), dtype=np.uint8)
    coordinates = np.zeros((len(candidate_ids), 2), dtype=np.int64)
    candidate_index = {candidate_id: index for index, candidate_id in enumerate(candidate_ids)}
    candidate_objects = {}
    log(f"validating and constructing {len(candidate_ids)} deduplicated candidate representations")
    for index, candidate_id in enumerate(candidate_ids):
        row = catalog[candidate_id]
        validate_candidate_reference(row, fasta)
        candidate = Candidate(
            candidate_id,
            row["chrom"],
            int(row["del_start0"]),
            int(row["del_end0"]),
            int(row["length"]),
        )
        candidate_objects[candidate_id] = candidate
        coordinates[index] = [candidate.del_start0, candidate.del_end0]
        refalt_tokens[index] = build_candidate_refalt_tokens(candidate, fasta.fetch)

    stem = f"pairsv_shard_{args.shard:02d}"
    if args.max_per_class_per_sample is not None:
        stem += f"_subset{args.max_per_class_per_sample}"
    h5_path = output / f"{stem}.h5"
    out_manifest = output / f"{stem}_manifest.tsv"
    runtime_path = output / f"{stem}_runtime.json"
    failure_categories = Counter()
    fetch_count = 0
    remote_seconds = 0.0
    completed = 0
    with PairSVShardWriter(h5_path, len(manifest_rows), shard_id=args.shard) as writer:
        writer.write_candidates(candidate_ids, refalt_tokens, coordinates)
        row_index = 0
        rows_by_sample = defaultdict(list)
        for row in manifest_rows:
            rows_by_sample[row["sample"]].append(row)
        for sample_id in sorted(rows_by_sample):
            sample = samples[sample_id]
            crai_path = temp / "crai" / f"{sample_id}.crai"
            measured_bytes += download_with_retries(sample["crai_url"], crai_path)
            log(f"opening {sample_id}: {len(rows_by_sample[sample_id])} candidates")
            with RemoteCramSession(
                sample["cram_url"],
                str(crai_path),
                str(reference),
                max_attempts=args.max_attempts,
            ) as session:
                for row in rows_by_sample[sample_id]:
                    candidate = candidate_objects[row["candidate_id"]]
                    common = {
                        **row,
                        "sample_id": sample_id,
                    }
                    try:
                        left, right, n_fetches, elapsed = session.fetch_breakpoints(candidate)
                        fetch_count += n_fetches
                        remote_seconds += elapsed
                        tensors = extract_example_from_reads(candidate, left, right, fasta.fetch)
                        if tensors.scalars[8] <= 0 or tensors.scalars[9] <= 0:
                            raise CandidateExtractionError("inadequate_flank_coverage")
                        writer.write_success(
                            row_index, common, tensors, candidate_index[candidate.candidate_id]
                        )
                        completed += 1
                    except CandidateExtractionError as exc:
                        category = str(exc).split(":", 1)[0]
                        failure_categories[category] += 1
                        writer.write_failure(
                            row_index,
                            common,
                            candidate_index[candidate.candidate_id],
                            str(exc),
                        )
                    row_index += 1
        writer.write_manifest(out_manifest)
    fasta.close()

    attempted = len(manifest_rows)
    failed = attempted - completed
    failure_rate = failed / attempted
    wall = time.time() - started_wall
    report = {
        "schema_version": "pairsv-runtime-v1",
        "shard": args.shard,
        "subset_per_class_per_sample": args.max_per_class_per_sample,
        "samples": sorted(samples),
        "candidates_attempted": attempted,
        "candidates_completed": completed,
        "candidates_failed": failed,
        "failure_rate": failure_rate,
        "failure_categories": dict(failure_categories),
        "remote_fetch_calls": fetch_count,
        "bytes_transferred_measurable_reference_and_crai": measured_bytes,
        "cram_range_bytes_transferred": None,
        "cram_range_bytes_note": "htslib/pysam does not expose HTTP range byte counts",
        "examples_per_second": completed / max(wall, 1e-9),
        "average_remote_time_per_attempted_example_seconds": remote_seconds / attempted,
        "remote_time_seconds": remote_seconds,
        "cache_size_bytes": directory_size(temp),
        "wall_time_seconds": wall,
        "output_hdf5": h5_path.name,
        "output_manifest": out_manifest.name,
        "reference_url": REFERENCE_URL,
        "reference_candidate_hash_checks": len(candidate_ids),
    }
    runtime_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    artifacts = [h5_path, out_manifest, runtime_path]
    if args.shard == 0:
        qc = qc_shard(
            h5_path,
            out_manifest,
            expected_split="val",
            require_literal_categories=True,
        )
        qc_path = output / f"{stem}_qc.json"
        save_qc_report(qc, qc_path)
        artifacts.append(qc_path)
        if qc["passed"]:
            figure_path = output / f"{stem}_representative_pileups.png"
            render_representative_pileups(h5_path, out_manifest, figure_path)
            artifacts.append(figure_path)
        else:
            failure_categories["qc_gate"] += 1
    checksum_path = output / f"{stem}_SHA256SUMS"
    write_checksums(artifacts, checksum_path)
    if failure_rate >= 0.01:
        raise SystemExit(f"extraction failure rate {failure_rate:.3%} exceeds the <1% gate")
    if args.shard == 0 and not qc["passed"]:
        raise SystemExit(f"shard-0 QC failed: {qc['problems']}")
    log(f"complete: attempted={attempted} completed={completed} failed={failed} wall={wall:.1f}s")


if __name__ == "__main__":
    main()

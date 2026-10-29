#!/usr/bin/env python3
"""Build the strict 50-person PAIR-SV manifest from the verified resources.

This replaces the superseded v2 manifest before production extraction.  It
does not redo source discovery or sample selection: the frozen 50-person split
is loaded from the completed kernel artifact and CRAM/CRAI URLs are parsed from
the official high-coverage sequence index.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import heapq
import json
import os
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlopen

import pysam
import numpy as np

from deepsv.multisample.manifest import (
    MANIFEST_SCHEMA_VERSION,
    af_bucket,
    assign_person_shards,
    gq_bucket,
    length_bucket,
    normalize_pure_deletion,
    stable_row_id,
    validate_pair_manifest,
)


PANGENIE_URL = (
    "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/data_collections/HGSVC2/"
    "release/v1.0/PanGenie_results/pangenie_merged_bi_nosnvs.vcf.gz"
)
SEQUENCE_INDEX_URL = (
    "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/data_collections/"
    "1000G_2504_high_coverage/1000G_2504_high_coverage.sequence.index"
)
MIN_GQ = 20
PER_CLASS = 1_000


def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {message}", flush=True)


def find_input_file(name: str, root: str = "/kaggle/input") -> Path:
    matches = sorted(Path(root).rglob(name)) if Path(root).exists() else []
    if not matches:
        raise FileNotFoundError(f"{name} was not found below {root}")
    return matches[0]


def download(url: str, path: Path) -> None:
    if path.exists() and path.stat().st_size:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["wget", "-q", "--tries=3", "--timeout=600", url, "-O", str(path)],
        check=True,
    )


def parse_official_sequence_index(url: str, wanted: set[str]) -> dict[str, tuple[str, str]]:
    text = urlopen(url, timeout=180).read().decode("utf-8", "replace")
    mapping: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        columns = line.split("\t")
        sample = next((value for value in columns if value in wanted), None)
        cram = next((value for value in columns if value.endswith(".cram")), None)
        if not sample or not cram:
            continue
        convert = lambda value: "https:" + value.split(":", 1)[1] if value.startswith("ftp:") else value
        exact_cram = convert(cram)
        # The official high-coverage sequence index publishes exact CRAM paths
        # but has no CRAI column. ENA serves each verified companion index at
        # the exact CRAM URL plus '.crai'; this is the convention already used
        # and passed by the completed CRAM POC. The CRAM URL itself is never
        # guessed or reconstructed.
        mapping[sample] = (exact_cram, exact_cram + ".crai")
    missing = sorted(wanted - set(mapping))
    if missing:
        raise RuntimeError(f"official sequence index lacks CRAM/CRAI mappings for {missing}")
    return mapping


def record_filter(rec) -> str | None:
    values = list(rec.filter.keys())
    if not values:
        return "."
    if values == ["PASS"] or set(values) == {"PASS"}:
        return "PASS"
    return None


def parse_gt(sample) -> tuple[str | None, int | None]:
    gt = sample.get("GT")
    gq = sample.get("GQ")
    if gt is None or len(gt) != 2 or any(value is None for value in gt):
        return None, None if gq is None else int(gq)
    if any(int(value) not in (0, 1) for value in gt):
        return None, None if gq is None else int(gq)
    return "/".join(map(str, gt)), None if gq is None else int(gq)


def af_value(rec) -> float | None:
    value = rec.info.get("AF")
    if isinstance(value, tuple):
        value = value[0] if value else None
    if value is None:
        ac, an = rec.info.get("AC"), rec.info.get("AN")
        if isinstance(ac, tuple):
            ac = ac[0] if ac else None
        value = float(ac) / float(an) if ac is not None and an else None
    return None if value is None else float(value)


def confidence_key(site: dict, sample: str) -> tuple:
    call = site["calls"][sample]
    digest = hashlib.sha256(f"{sample}|{site['candidate_id']}|pairsv-v3".encode()).hexdigest()
    return (-call["gq"], -float(site["qual"] or 0.0), digest)


def stratum(site: dict, sample: str, include_gq: bool = False) -> tuple[str, ...]:
    key = (site["chrom"], site["length_bucket"], site["af_bucket"], site["repeat_bucket"])
    return key + ((gq_bucket(site["calls"][sample]["gq"]),) if include_gq else ())


def proportional_top_select(sites: list[dict], sample: str, n: int) -> list[dict]:
    """Proportional stratification with confidence ranking inside each stratum."""
    buckets: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for site in sites:
        buckets[stratum(site, sample)].append(site)
    for values in buckets.values():
        values.sort(key=lambda site: confidence_key(site, sample))
    total = sum(map(len, buckets.values()))
    heap = []
    selected_count = Counter()
    for key, values in buckets.items():
        # Lower selected/available ratio is popped first, yielding proportional coverage.
        heapq.heappush(heap, (0.0, key))
    output = []
    while heap and len(output) < min(n, total):
        _, key = heapq.heappop(heap)
        index = selected_count[key]
        output.append(buckets[key][index])
        selected_count[key] += 1
        if selected_count[key] < len(buckets[key]):
            ratio = selected_count[key] / len(buckets[key])
            heapq.heappush(heap, (ratio, key))
    return output


def overlaps_conflict(site: dict, intervals: list[tuple[int, int, str]], starts: list[int]) -> bool:
    left, right = site["del_start0"], site["del_end0"]
    stop = bisect.bisect_left(starts, right)
    index = stop - 1
    while index >= 0 and intervals[index][0] >= left - 10_000:
        other_left, other_right, other_id = intervals[index]
        if other_id != site["candidate_id"] and other_right > left and other_left < right:
            return True
        index -= 1
    return False


def select_continuous_matches(
    eligible: list[dict], target_positives: list[dict], sample: str, n: int
) -> list[dict]:
    """Select sites that continuously match a target site's QC metadata.

    AF is matched continuously because the broad reporting buckets are not
    sufficient to prevent a candidate-frequency shortcut. Scarce high-AF 0/0
    calls are allocated first. Chromosome, deletion length and GQ then break
    ties inside a narrow AF neighbourhood. The algorithm is deterministic and
    selects each candidate at most once for a person.
    """
    if n > len(eligible) or n > len(target_positives):
        return []

    def numeric_af(site: dict) -> float:
        return -1.0 if site["af"] is None else float(site["af"])

    def secondary_cost(target: dict, candidate: dict) -> tuple:
        target_gq = int(target["calls"][sample]["gq"])
        candidate_gq = int(candidate["calls"][sample]["gq"])
        return (
            abs(numeric_af(target) - numeric_af(candidate)),
            target["length_bucket"] != candidate["length_bucket"],
            abs(np.log1p(target["length"]) - np.log1p(candidate["length"])),
            target["chrom"] != candidate["chrom"],
            gq_bucket(target_gq) != gq_bucket(candidate_gq),
            abs(np.log1p(target_gq) - np.log1p(candidate_gq)),
            confidence_key(candidate, sample),
        )

    # A sorted list keeps the nearest-AF search deterministic. Processing the
    # upper AF tail first prevents abundant low-AF targets consuming the rare
    # high-AF callable 0/0 sites.
    available = sorted(eligible, key=lambda site: (numeric_af(site), site["candidate_id"]))
    available_afs = [numeric_af(site) for site in available]
    targets = sorted(
        target_positives[:n],
        key=lambda site: (-numeric_af(site), site["candidate_id"]),
    )
    output = []
    neighbourhood = 32
    for target in targets:
        insertion = bisect.bisect_left(available_afs, numeric_af(target))
        left = max(0, insertion - neighbourhood)
        right = min(len(available), insertion + neighbourhood)
        if left == right:
            left, right = 0, len(available)
        best_index = min(
            range(left, right),
            key=lambda index: secondary_cost(target, available[index]),
        )
        output.append(available.pop(best_index))
        available_afs.pop(best_index)
    return output


def select_matched_negatives(
    eligible: list[dict], target_positives: list[dict], sample: str, n: int
) -> list[dict]:
    """Compatibility wrapper naming the final 0/0 matching operation."""
    return select_continuous_matches(eligible, target_positives, sample, n)


def build_conflict_free_negative_ids(
    sites: list[dict], people: list[str]
) -> tuple[dict[str, set[str]], Counter]:
    """Return all callable, conflict-free 0/0 candidate IDs per person."""
    carried = {}
    for sample in people:
        intervals = sorted(
            (site["del_start0"], site["del_end0"], site["candidate_id"])
            for site in sites
            if site["calls"].get(sample, {}).get("gt") in {"0/1", "1/0", "1/1"}
        )
        carried[sample] = (intervals, [item[0] for item in intervals])
    eligible_ids: dict[str, set[str]] = {sample: set() for sample in people}
    rejected = Counter()
    for sample in people:
        intervals, starts = carried[sample]
        for site in sites:
            if site["calls"].get(sample, {}).get("gt") != "0/0":
                continue
            if overlaps_conflict(site, intervals, starts):
                rejected[sample] += 1
                continue
            eligible_ids[sample].add(site["candidate_id"])
    return eligible_ids, rejected


def load_sites(vcf_path: Path, people: list[str]) -> tuple[list[dict], Counter]:
    vcf = pysam.VariantFile(str(vcf_path))
    missing = sorted(set(people) - set(vcf.header.samples))
    if missing:
        raise RuntimeError(f"PanGenie VCF lacks frozen people: {missing}")
    sites: list[dict] = []
    rejected = Counter()
    for chromosome_index in range(1, 23):
        chrom = f"chr{chromosome_index}"
        for rec in vcf.fetch(chrom):
            if not rec.alts or len(rec.alts) != 1 or rec.alts[0].startswith("<"):
                rejected["not_biallelic_sequence_resolved"] += 1
                continue
            selected_filter = record_filter(rec)
            if selected_filter is None:
                rejected["site_filter"] += 1
                continue
            try:
                start, end = normalize_pure_deletion(rec.start, rec.ref, rec.alts[0])
            except ValueError:
                rejected["not_pure_deletion"] += 1
                continue
            length = end - start
            if not 50 <= length <= 10_000:
                rejected["length"] += 1
                continue
            calls = {}
            for sample in people:
                gt, gq = parse_gt(rec.samples[sample])
                if gt is None or gq is None or gq < MIN_GQ:
                    continue
                if gt in {"0/0", "0/1", "1/0", "1/1"}:
                    calls[sample] = {"gt": gt, "gq": gq}
            if not calls:
                rejected["no_callable_frozen_person"] += 1
                continue
            allele_frequency = af_value(rec)
            ref_hash = hashlib.sha256(rec.ref.upper().encode()).hexdigest()
            alt_hash = hashlib.sha256(rec.alts[0].upper().encode()).hexdigest()
            candidate_id = f"{chrom}:{start}-{end}:{ref_hash[:10]}"
            sites.append(
                {
                    "candidate_id": candidate_id,
                    "chrom": chrom,
                    "vcf_pos_1based": rec.pos,
                    "ref_start0": rec.start,
                    "ref_length": len(rec.ref),
                    "alt_length": len(rec.alts[0]),
                    "del_start0": start,
                    "del_end0": end,
                    "length": length,
                    "af": allele_frequency,
                    "length_bucket": length_bucket(length),
                    "af_bucket": af_bucket(allele_frequency),
                    "repeat_bucket": "annotation_unavailable",
                    "site_filter": selected_filter,
                    "qual": None if rec.qual is None else float(rec.qual),
                    "ref_sha256": ref_hash,
                    "alt_sha256": alt_hash,
                    "calls": calls,
                }
            )
        log(f"parsed {chrom}: retained={len(sites)}")
    return sites, rejected


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def metadata_leakage_probe(rows: list[dict]) -> dict[str, object]:
    """Probe label prediction from QC-only metadata plus candidate length/AF."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    x = np.asarray(
        [
            [
                np.log1p(float(row["length"])),
                -1.0 if row["af"] is None else float(row["af"]),
                np.log1p(float(row["genotype_quality"])),
            ]
            for row in rows
        ],
        dtype=np.float64,
    )
    y = np.asarray([int(row["label"]) for row in rows], dtype=np.uint8)
    fold_aucs = []
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=20260719)
    for train, test in splitter.split(x, y):
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=20260719))
        model.fit(x[train], y[train])
        fold_aucs.append(float(roc_auc_score(y[test], model.predict_proba(x[test])[:, 1])))
    mean_auc = float(np.mean(fold_aucs))
    return {
        "features": ["log1p_length", "allele_frequency", "log1p_genotype_quality"],
        "five_fold_roc_auc": fold_aucs,
        "mean_roc_auc": mean_auc,
        "warning_threshold": 0.65,
        "passed": mean_auc < 0.65,
        "note": "sample/population are exactly class-balanced per person and are never model inputs",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="/kaggle/working")
    parser.add_argument("--input-root", default="/kaggle/input")
    parser.add_argument("--vcf", default=None)
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    split_path = find_input_file("split_manifest.json", args.input_root)
    frozen = json.loads(split_path.read_text())
    people = sorted(frozen)
    if len(people) != 50:
        raise RuntimeError(f"frozen manifest contains {len(people)} people, expected 50")
    shards = assign_person_shards(frozen)
    official_mapping = parse_official_sequence_index(SEQUENCE_INDEX_URL, set(people))

    vcf_path = Path(args.vcf) if args.vcf else Path("/kaggle/temp/pangenie_merged_bi_nosnvs.vcf.gz")
    download(PANGENIE_URL, vcf_path)
    download(PANGENIE_URL + ".tbi", Path(str(vcf_path) + ".tbi"))
    sites, rejected = load_sites(vcf_path, people)
    by_id = {site["candidate_id"]: site for site in sites}

    negative_ids, conflict_rejections = build_conflict_free_negative_ids(sites, people)
    people_by_split = {
        split: [sample for sample in people if frozen[sample]["split"] == split]
        for split in ("train", "val", "test")
    }
    pairable_ids_by_split = {}
    for split, split_people in people_by_split.items():
        positive_ids = {
            site["candidate_id"]
            for site in sites
            if any(
                site["calls"].get(sample, {}).get("gt") in {"0/1", "1/0", "1/1"}
                for sample in split_people
            )
        }
        callable_negative_ids = set().union(*(negative_ids[sample] for sample in split_people))
        pairable_ids_by_split[split] = positive_ids & callable_negative_ids

    selected_positives: dict[str, list[dict]] = {}
    for sample in people:
        pairable = pairable_ids_by_split[frozen[sample]["split"]]
        eligible_positives = [
            site for site in sites
            if site["candidate_id"] in pairable
            and site["calls"].get(sample, {}).get("gt") in {"0/1", "1/0", "1/1"}
        ]
        # Select a deterministic, high-confidence proxy distribution from the
        # person's full callable 0/0 support, then choose positive sites that
        # continuously match it. This places both classes on common metadata
        # support before the selected-positive union is formed.
        negative_proxy_pool = [
            by_id[candidate_id]
            for candidate_id in negative_ids[sample] & pairable
        ]
        negative_proxy_targets = proportional_top_select(negative_proxy_pool, sample, PER_CLASS)
        selected_positives[sample] = select_continuous_matches(
            eligible_positives, negative_proxy_targets, sample, PER_CLASS
        )
        if len(selected_positives[sample]) != PER_CLASS:
            raise RuntimeError(
                f"{sample} has only {len(selected_positives[sample])} metadata-matchable positives "
                f"(positive_pool={len(eligible_positives)}, negative_proxy_pool={len(negative_proxy_pool)})"
            )
    positive_union_by_split = {
        split: {
            site["candidate_id"]
            for sample, values in selected_positives.items()
            if frozen[sample]["split"] == split
            for site in values
        }
        for split in ("train", "val", "test")
    }

    selected_negatives: dict[str, list[dict]] = {}
    for sample in people:
        eligible = [
            by_id[candidate_id]
            for candidate_id in positive_union_by_split[frozen[sample]["split"]]
            if candidate_id in negative_ids[sample]
        ]
        selected_negatives[sample] = select_matched_negatives(
            eligible, selected_positives[sample], sample, PER_CLASS
        )
        if len(selected_negatives[sample]) != PER_CLASS:
            raise RuntimeError(f"{sample} has only {len(selected_negatives[sample])} matched conflict-free negatives")

    manifest_rows = []
    for sample in people:
        common = {
            "sample": sample,
            "super_pop": frozen[sample]["super_pop"],
            "split": frozen[sample]["split"],
            "shard": shards[sample],
            "source_filename": Path(PANGENIE_URL).name,
            "label_provenance": "HGSVC2_PanGenie_silver",
            "callable_by_genotype": 1,
            "conflict_free": 1,
        }
        for label, negative_type, selected in (
            (1, "not_applicable", selected_positives[sample]),
            (0, "same_site_negative", selected_negatives[sample]),
        ):
            for site in selected:
                call = site["calls"][sample]
                manifest_rows.append(
                    {
                        "row_id": stable_row_id(sample, site["candidate_id"]),
                        **common,
                        "candidate_id": site["candidate_id"],
                        "label": label,
                        "genotype": call["gt"],
                        "genotype_quality": call["gq"],
                        "gq_bucket": gq_bucket(call["gq"]),
                        "negative_type": negative_type,
                        **{key: site[key] for key in (
                            "chrom", "del_start0", "del_end0", "length", "af",
                            "length_bucket", "af_bucket", "repeat_bucket", "site_filter"
                        )},
                    }
                )
    manifest_rows.sort(key=lambda row: (int(row["shard"]), row["sample"], -int(row["label"]), row["candidate_id"]))

    used_ids = {row["candidate_id"] for row in manifest_rows}
    catalog_rows = [
        {key: site[key] for key in (
            "candidate_id", "chrom", "vcf_pos_1based", "ref_start0", "ref_length", "alt_length",
            "del_start0", "del_end0", "length", "af", "length_bucket", "af_bucket",
            "repeat_bucket", "site_filter", "qual", "ref_sha256", "alt_sha256"
        )}
        for site in sites if site["candidate_id"] in used_ids
    ]
    catalog_rows.sort(key=lambda row: row["candidate_id"])
    sample_rows = [
        {
            "sample": sample,
            "super_pop": frozen[sample]["super_pop"],
            "split": frozen[sample]["split"],
            "shard": shards[sample],
            "cram_url": official_mapping[sample][0],
            "crai_url": official_mapping[sample][1],
            "mapping_source": SEQUENCE_INDEX_URL,
            "crai_mapping_policy": "verified_ENA_companion_index_exact_cram_url_plus_.crai",
        }
        for sample in people
    ]
    write_tsv(output / "sample_candidate_manifest.tsv", manifest_rows, list(manifest_rows[0]))
    write_tsv(output / "candidate_catalog.tsv", catalog_rows, list(catalog_rows[0]))
    write_tsv(output / "sample_cram_manifest.tsv", sample_rows, list(sample_rows[0]))
    (output / "split_manifest.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    (output / "shard_manifest.json").write_text(json.dumps(shards, indent=2, sort_keys=True) + "\n")

    audit = validate_pair_manifest(output / "sample_candidate_manifest.tsv")
    gq_by_label = defaultdict(list)
    for row in manifest_rows:
        gq_by_label[str(row["label"])].append(int(row["genotype_quality"]))
    paired = Counter(row["candidate_id"] for row in manifest_rows)
    labels_by_candidate = defaultdict(set)
    for row in manifest_rows:
        labels_by_candidate[row["candidate_id"]].add(int(row["label"]))
    leakage_probe = metadata_leakage_probe(manifest_rows)
    qc = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_audit": audit,
        "selected_site_filter_policy": "FILTER is PASS or unfiltered '.'; all other FILTER values rejected",
        "callability_policy": "diploid non-missing GT plus GQ>=20; adequate read coverage is a mandatory extraction gate",
        "conflict_policy": "0/0 negatives overlapping another carried GQ>=20 deletion are rejected",
        "pairability_policy": "positive loci must have a callable conflict-free 0/0 carrier in the same frozen split",
        "positive_sampling_policy": "high-confidence stratified 0/0 proxy distribution followed by continuous metadata matching on pairable positive loci",
        "negative_matching_policy": "continuous AF nearest-neighbour matching; length, chromosome and GQ are deterministic secondary criteria",
        "repeat_stratification": "annotation unavailable; repeat_bucket is explicitly annotation_unavailable",
        "site_rejections": dict(rejected),
        "conflicting_negative_rejections": dict(conflict_rejections),
        "pairable_candidates_by_split": {
            split: len(values) for split, values in pairable_ids_by_split.items()
        },
        "manifest_rows": len(manifest_rows),
        "unique_candidates": len(used_ids),
        "candidates_reused_across_people": sum(value > 1 for value in paired.values()),
        "same_site_positive_negative_candidates": sum(labels == {0, 1} for labels in labels_by_candidate.values()),
        "gq_quantiles_selected": {
            label: {name: float(np.quantile(values, q)) for name, q in (("p05", .05), ("p50", .5), ("p95", .95))}
            for label, values in gq_by_label.items()
        },
        "length_bucket_counts": dict(Counter(row["length_bucket"] for row in manifest_rows)),
        "af_bucket_counts": dict(Counter(row["af_bucket"] for row in manifest_rows)),
        "gq_bucket_counts": dict(Counter(row["gq_bucket"] for row in manifest_rows)),
        "metadata_only_leakage_probe": leakage_probe,
        "per_person_counts": {
            sample: dict(Counter(str(row["label"]) for row in manifest_rows if row["sample"] == sample))
            for sample in people
        },
    }
    (output / "label_qc.json").write_text(json.dumps(qc, indent=2, sort_keys=True) + "\n")
    if not audit["passed"]:
        raise SystemExit(f"manifest audit failed: {audit['problems'][:10]}")
    if not leakage_probe["passed"]:
        raise SystemExit(f"metadata-only leakage probe failed: {leakage_probe}")
    log(f"PAIR-SV manifest complete: rows={len(manifest_rows)} candidates={len(used_ids)}")


if __name__ == "__main__":
    main()

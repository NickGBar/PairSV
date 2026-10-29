"""Strict manifest rules for the 50-person PAIR-SV experiment.

The functions in this module are deliberately independent of ``pysam`` so the
coordinate, split, and leakage contracts can be unit-tested without the 1.6 GB
PanGenie VCF.  The Kaggle manifest builder applies these functions while
streaming the callset.
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence


MANIFEST_SCHEMA_VERSION = "pairsv-manifest-v3"
VALID_BASES = frozenset("ACGTN")
MODEL_FORBIDDEN_FIELDS = frozenset(
    {
        "sample",
        "sample_id",
        "super_pop",
        "population",
        "split",
        "label_provenance",
        "negative_type",
        "neg_type",
        "source_filename",
        "genotype_quality",
        "gq",
        "read_name_hash",
    }
)


def normalize_pure_deletion(ref_start0: int, ref: str, alt: str) -> tuple[int, int]:
    """Return the deleted 0-based half-open interval for a pure deletion.

    Common prefix and suffix bases are trimmed.  A record is accepted only if
    the remaining ALT allele is empty and the remaining REF allele is nonempty;
    this rejects symbolic alleles and deletion/substitution hybrids.
    """
    ref = (ref or "").upper()
    alt = (alt or "").upper()
    if not ref or not alt or set(ref) - VALID_BASES or set(alt) - VALID_BASES:
        raise ValueError("REF/ALT must be non-empty sequence alleles over A/C/G/T/N")
    if len(ref) <= len(alt):
        raise ValueError("record is not a deletion")

    prefix = 0
    max_prefix = min(len(ref), len(alt))
    while prefix < max_prefix and ref[prefix] == alt[prefix]:
        prefix += 1

    suffix = 0
    max_suffix = min(len(ref) - prefix, len(alt) - prefix)
    while suffix < max_suffix and ref[-1 - suffix] == alt[-1 - suffix]:
        suffix += 1

    ref_end = len(ref) - suffix if suffix else len(ref)
    alt_end = len(alt) - suffix if suffix else len(alt)
    ref_core = ref[prefix:ref_end]
    alt_core = alt[prefix:alt_end]
    if not ref_core or alt_core:
        raise ValueError("record is a complex delins, not a sequence-resolved pure deletion")
    return int(ref_start0 + prefix), int(ref_start0 + ref_end)


def length_bucket(length: int) -> str:
    bounds = (
        (50, 100, "50-99"),
        (100, 200, "100-199"),
        (200, 500, "200-499"),
        (500, 1_000, "500-999"),
        (1_000, 2_000, "1k-2k"),
        (2_000, 5_000, "2k-5k"),
        (5_000, 10_001, "5k-10k"),
    )
    for low, high, name in bounds:
        if low <= int(length) < high:
            return name
    return "out_of_range"


def af_bucket(af: float | None) -> str:
    if af is None:
        return "missing"
    if af < 0.01:
        return "very_rare"
    if af < 0.05:
        return "rare"
    if af < 0.20:
        return "low_frequency"
    return "common"


def gq_bucket(gq: int | float) -> str:
    value = float(gq)
    if value < 20:
        return "below_policy"
    if value < 50:
        return "20-49"
    if value < 100:
        return "50-99"
    if value < 1_000:
        return "100-999"
    return "1000+"


def stable_row_id(sample: str, candidate_id: str) -> str:
    digest = hashlib.sha256(f"{MANIFEST_SCHEMA_VERSION}|{sample}|{candidate_id}".encode()).hexdigest()
    return f"pairsv-{digest[:24]}"


def assign_person_shards(
    people: Mapping[str, Mapping[str, str]],
) -> dict[str, int]:
    """Assign shard 0=validation, 1..8=train, 9=internal test.

    Each train shard contains one person from each super-population where the
    frozen 40/5/5 design is ancestry balanced.
    """
    by_split: dict[str, list[str]] = defaultdict(list)
    for sample, meta in people.items():
        by_split[str(meta["split"])].append(sample)
    expected = {"train": 40, "val": 5, "test": 5}
    observed = {name: len(by_split.get(name, [])) for name in expected}
    if observed != expected:
        raise ValueError(f"expected frozen 40/5/5 split, observed {observed}")

    result = {sample: 0 for sample in sorted(by_split["val"])}
    result.update({sample: 9 for sample in sorted(by_split["test"])})
    train_by_pop: dict[str, list[str]] = defaultdict(list)
    for sample in by_split["train"]:
        train_by_pop[str(people[sample]["super_pop"])].append(sample)
    if sorted(map(len, train_by_pop.values())) != [8, 8, 8, 8, 8]:
        raise ValueError("train split must contain eight people in each of five super-populations")
    for samples in train_by_pop.values():
        samples.sort()
    for shard_offset in range(8):
        for pop in sorted(train_by_pop):
            result[train_by_pop[pop][shard_offset]] = 1 + shard_offset
    return result


def _load_rows(path_or_rows: str | Path | Iterable[Mapping[str, object]]) -> list[dict[str, str]]:
    if isinstance(path_or_rows, (str, Path)):
        with Path(path_or_rows).open(newline="") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))
    return [{str(k): str(v) for k, v in row.items()} for row in path_or_rows]


def validate_pair_manifest(
    path_or_rows: str | Path | Iterable[Mapping[str, object]],
    *,
    expected_people: int = 50,
    expected_per_class_per_person: int = 1_000,
) -> dict[str, object]:
    """Validate the non-negotiable label, coordinate, balance, and split rules."""
    rows = _load_rows(path_or_rows)
    problems: list[str] = []
    required = {
        "row_id",
        "sample",
        "candidate_id",
        "split",
        "shard",
        "label",
        "genotype",
        "genotype_quality",
        "negative_type",
        "chrom",
        "del_start0",
        "del_end0",
        "length",
        "site_filter",
        "callable_by_genotype",
        "conflict_free",
    }
    if not rows:
        return {"passed": False, "problems": ["manifest is empty"], "rows": 0}
    missing = sorted(required - set(rows[0]))
    if missing:
        problems.append(f"missing required fields: {missing}")

    seen_ids: set[str] = set()
    counts: Counter[tuple[str, int]] = Counter()
    samples: dict[str, set[str]] = defaultdict(set)
    candidate_labels: dict[str, set[int]] = defaultdict(set)
    min_gq = float("inf")
    for index, row in enumerate(rows):
        try:
            label = int(row["label"])
            gq = float(row["genotype_quality"])
            start = int(row["del_start0"])
            end = int(row["del_end0"])
            length = int(row["length"])
            shard = int(row["shard"])
        except (KeyError, TypeError, ValueError) as exc:
            problems.append(f"row {index} has invalid typed field: {exc}")
            continue
        min_gq = min(min_gq, gq)
        row_id = row.get("row_id", "")
        if not row_id or row_id in seen_ids:
            problems.append(f"row {index} has empty or duplicate row_id")
        seen_ids.add(row_id)
        if gq < 20:
            problems.append(f"row {index} violates GQ>=20")
        gt = row.get("genotype")
        if label == 1 and gt not in {"0/1", "1/0", "1/1"}:
            problems.append(f"row {index} positive has invalid GT {gt!r}")
        if label == 0 and gt != "0/0":
            problems.append(f"row {index} negative has invalid GT {gt!r}")
        if label == 0 and row.get("negative_type") != "same_site_negative":
            problems.append(f"row {index} is not a same-site negative")
        if end - start != length or not (50 <= length <= 10_000):
            problems.append(f"row {index} has inconsistent/out-of-range coordinates")
        if row.get("site_filter") not in {"PASS", "."}:
            problems.append(f"row {index} fails selected site-filter policy")
        if row.get("callable_by_genotype") not in {"1", "True", "true"}:
            problems.append(f"row {index} is not genotype-callable")
        if row.get("conflict_free") not in {"1", "True", "true"}:
            problems.append(f"row {index} overlaps a conflicting carried deletion")
        split = row.get("split", "")
        expected_shard = 0 if split == "val" else (9 if split == "test" else None)
        if expected_shard is not None and shard != expected_shard:
            problems.append(f"row {index} has split/shard mismatch")
        counts[(row.get("sample", ""), label)] += 1
        samples[row.get("sample", "")].add(split)
        candidate_labels[row.get("candidate_id", "")].add(label)

    if len(samples) != expected_people:
        problems.append(f"expected {expected_people} people, found {len(samples)}")
    for sample, splits in samples.items():
        if len(splits) != 1:
            problems.append(f"sample {sample} appears in multiple splits: {sorted(splits)}")
        for label in (0, 1):
            count = counts[(sample, label)]
            if count != expected_per_class_per_person:
                problems.append(
                    f"sample {sample} label {label}: expected {expected_per_class_per_person}, found {count}"
                )
    paired_candidates = sum(labels == {0, 1} for labels in candidate_labels.values())
    if paired_candidates == 0:
        problems.append("no candidate is shared by a positive and a same-site negative")
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "passed": not problems,
        "rows": len(rows),
        "people": len(samples),
        "positives": sum(count for (sample, label), count in counts.items() if label == 1),
        "negatives": sum(count for (sample, label), count in counts.items() if label == 0),
        "min_gq": None if min_gq == float("inf") else min_gq,
        "paired_candidates": paired_candidates,
        "problem_count": len(problems),
        "problems": problems[:200],
    }


def model_tensor_field_audit(field_names: Sequence[str]) -> dict[str, object]:
    leaked = sorted(set(map(str.lower, field_names)) & MODEL_FORBIDDEN_FIELDS)
    return {"passed": not leaked, "forbidden_fields_present": leaked}

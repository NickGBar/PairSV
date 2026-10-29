"""Shard-0 quality gate and representative pileup visualizations."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import h5py
import numpy as np

from .extraction import IMAGE_SHAPE, READ_MASK_SHAPE, READ_TOKEN_SHAPE, SCALAR_FEATURE_NAMES
from .storage import MODEL_TENSOR_DATASETS, SHARD_SCHEMA_VERSION


def _read_manifest(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def qc_shard(
    h5_path: str | Path,
    manifest_path: str | Path,
    *,
    expected_split: str = "val",
    max_failure_rate: float = 0.01,
    require_literal_categories: bool = False,
) -> dict[str, object]:
    rows = _read_manifest(manifest_path)
    problems: list[str] = []
    warnings: list[str] = []
    with h5py.File(h5_path, "r") as h5:
        schema = h5.attrs.get("schema_version", "")
        if schema != SHARD_SCHEMA_VERSION:
            problems.append(f"schema mismatch: {schema!r}")
        examples = h5["examples"]
        expected_shapes = {
            "images": (len(rows),) + IMAGE_SHAPE,
            "read_tokens": (len(rows),) + READ_TOKEN_SHAPE,
            "read_mask": (len(rows),) + READ_MASK_SHAPE,
            "scalars": (len(rows), len(SCALAR_FEATURE_NAMES)),
        }
        for name, expected in expected_shapes.items():
            if examples[name].shape != expected:
                problems.append(f"{name} shape {examples[name].shape}, expected {expected}")
        success = examples["success"][:].astype(bool)
        labels = examples["label"][:]
        failure_rate = 1.0 - float(success.mean()) if len(success) else 1.0
        if failure_rate >= max_failure_rate:
            problems.append(f"failure rate {failure_rate:.4%} is not below {max_failure_rate:.2%}")
        if success.any():
            if not np.isfinite(examples["scalars"][success]).all():
                problems.append("successful examples contain non-finite scalars")
            masks = examples["read_mask"][success]
            if np.any(masks.sum(axis=(1, 2)) == 0):
                problems.append("successful example has no selected reads")
            images = examples["images"][success]
            if np.any(images.reshape(len(images), -1).sum(axis=1) == 0):
                problems.append("successful example has an empty paired pileup")
        if Counter(labels[success].tolist()) and len(set(labels[success].tolist())) != 2:
            problems.append("successful class balance contains only one class")

        model_fields = tuple(json.loads(h5.attrs["model_tensor_datasets"]))
        if model_fields != MODEL_TENSOR_DATASETS:
            problems.append("model tensor whitelist differs from the versioned schema")
        forbidden_tokens = ("sample", "population", "split", "negative", "filename", "gq", "hash")
        leaked = [field for field in model_fields if any(token in field.lower() for token in forbidden_tokens)]
        if leaked:
            problems.append(f"forbidden metadata entered model tensors: {leaked}")

        candidate_ids = [value.decode() if isinstance(value, bytes) else str(value) for value in examples["candidate_id"][:]]
        sample_ids = [value.decode() if isinstance(value, bytes) else str(value) for value in examples["sample_id"][:]]
        breakpoints = examples["breakpoints"][:]
        shared: dict[str, list[int]] = defaultdict(list)
        for index, cid in enumerate(candidate_ids):
            if success[index]:
                shared[cid].append(index)
        paired_candidates = 0
        sample_specific_differences = 0
        for cid, indices in shared.items():
            paired = [index for index in indices if labels[index] == 1]
            negative = [index for index in indices if labels[index] == 0]
            if not paired or not negative:
                continue
            left, right = paired[0], negative[0]
            paired_candidates += 1
            if sample_ids[left] == sample_ids[right]:
                problems.append(f"candidate {cid} has positive/negative labels in one sample")
            if not np.array_equal(breakpoints[left], breakpoints[right]):
                problems.append(f"candidate {cid} coordinate mismatch across people")
            differs = not np.array_equal(examples["images"][left], examples["images"][right])
            differs |= not np.array_equal(examples["read_tokens"][left], examples["read_tokens"][right])
            if differs:
                sample_specific_differences += 1
        if paired_candidates == 0:
            problems.append("no extracted positive/negative candidate pair is available")
        elif sample_specific_differences != paired_candidates:
            problems.append("some same-candidate cross-person inputs are byte-identical")

        candidate_key = [value.decode() if isinstance(value, bytes) else str(value) for value in h5["candidates/candidate_id"][:]]
        if len(candidate_key) != len(set(candidate_key)):
            problems.append("candidate-level REF/ALT representation is not deduplicated")
        refalt = h5["candidates/refalt_tokens"][:]
        if refalt.shape[1:] != (2, 1024):
            problems.append(f"candidate REF/ALT shape is {refalt.shape}")
        if np.all(refalt[:, 0] == refalt[:, 1], axis=1).any() if len(refalt) else False:
            warnings.append("at least one candidate REF and ALT token array may be identical")

    split_counts = Counter(row.get("split", "") for row in rows)
    if split_counts != Counter({expected_split: len(rows)}):
        problems.append(f"shard contains unexpected person splits: {dict(split_counts)}")
    gqs = [float(row["genotype_quality"]) for row in rows]
    if gqs and min(gqs) < 20:
        problems.append("shard manifest violates GQ>=20")
    labels_manifest = Counter(int(row["label"]) for row in rows)
    samples = sorted(set(row["sample"] for row in rows))
    failure_categories = Counter(row.get("failure_reason", "") or "success" for row in rows)
    successful_rows = [row for row in rows if row.get("extraction_success") == "1"]
    literal_categories = {
        "short_50_200": any(row["label"] == "1" and 50 <= int(row["length"]) <= 200 for row in successful_rows),
        "medium_201_1999": any(row["label"] == "1" and 200 < int(row["length"]) < 2_000 for row in successful_rows),
        "long_2000_10000": any(row["label"] == "1" and int(row["length"]) >= 2_000 for row in successful_rows),
        "heterozygous_positive": any(row.get("genotype") in {"0/1", "1/0"} for row in successful_rows),
        "homozygous_alt_positive": any(row.get("genotype") == "1/1" for row in successful_rows),
        "same_site_negative": any(row["label"] == "0" for row in successful_rows),
    }
    missing_literal = [name for name, present in literal_categories.items() if not present]
    if require_literal_categories and missing_literal:
        problems.append(f"mandatory literal QC categories missing: {missing_literal}")
    report = {
        "schema_version": SHARD_SCHEMA_VERSION,
        "passed": not problems,
        "problem_count": len(problems),
        "problems": problems,
        "warnings": warnings,
        "examples": len(rows),
        "samples": samples,
        "class_counts_manifest": dict(labels_manifest),
        "failure_rate": failure_rate,
        "failure_categories": dict(failure_categories),
        "min_gq": min(gqs) if gqs else None,
        "paired_candidates_checked": paired_candidates,
        "sample_specific_pairs_differing": sample_specific_differences,
        "literal_example_categories": literal_categories,
        "model_tensor_datasets": MODEL_TENSOR_DATASETS,
        "locus_cluster_leakage": "not_applicable_protocol_A; protocol_B requires a frozen locus-cluster split",
    }
    return report


def save_qc_report(report: dict[str, object], path: str | Path) -> None:
    Path(path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def render_representative_pileups(
    h5_path: str | Path,
    manifest_path: str | Path,
    output_path: str | Path,
    *,
    max_examples: int = 8,
) -> list[str]:
    """Render deterministic short/medium/long, GT, and negative examples."""
    import matplotlib.pyplot as plt

    rows = _read_manifest(manifest_path)
    categories = (
        ("short_positive", lambda row: row["label"] == "1" and int(row["length"]) <= 200),
        ("medium_positive", lambda row: row["label"] == "1" and 200 < int(row["length"]) < 2_000),
        ("long_positive", lambda row: row["label"] == "1" and int(row["length"]) >= 2_000),
        ("heterozygous", lambda row: row.get("genotype") in {"0/1", "1/0"}),
        ("homozygous_alt", lambda row: row.get("genotype") == "1/1"),
        ("same_site_negative", lambda row: row["label"] == "0"),
    )
    selected: list[tuple[str, int]] = []
    used = set()
    for name, predicate in categories:
        for index, row in enumerate(rows):
            if index not in used and row.get("extraction_success") == "1" and predicate(row):
                selected.append((name, index))
                used.add(index)
                break
    selected = selected[:max_examples]
    if not selected:
        raise ValueError("no successful examples available for visualization")
    with h5py.File(h5_path, "r") as h5:
        figure, axes = plt.subplots(len(selected), 2, figsize=(12, 2.2 * len(selected)), squeeze=False)
        for row_index, (category, example_index) in enumerate(selected):
            image = h5["examples/images"][example_index]
            for side in range(2):
                # Compress the six channels to a legible 64x128 QC heatmap.
                axes[row_index, side].imshow(image[side].mean(axis=0), aspect="auto", cmap="viridis")
                axes[row_index, side].set_title(f"{category} | {'left' if side == 0 else 'right'}")
                axes[row_index, side].set_ylabel(rows[example_index]["row_id"][:18])
        figure.tight_layout()
        figure.savefig(output_path, dpi=150)
        plt.close(figure)
    return [rows[index]["row_id"] for _, index in selected]

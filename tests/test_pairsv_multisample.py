from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import pysam
import pytest

from scripts.build_pairsv_manifest import select_matched_negatives

from deepsv.multisample.extraction import (
    IMAGE_SHAPE,
    READ_MASK_SHAPE,
    READ_TOKEN_SHAPE,
    SCALAR_FEATURE_NAMES,
    Candidate,
    build_candidate_refalt_tokens,
    extract_example_from_reads,
    select_reads,
    selection_reason,
)
from deepsv.multisample.manifest import (
    assign_person_shards,
    normalize_pure_deletion,
    validate_pair_manifest,
)
from deepsv.multisample.qc import qc_shard
from deepsv.multisample.storage import PairSVShardWriter, sha256_file, write_checksums
from deepsv.multisample.dataset import PairSVHDF5Dataset, ScalarNormalizer
from scripts.extract_pairsv_shard import deterministic_subset
from scripts.embed_pairsv_refalt import tokens_to_sequence


def fake_read(
    name: str,
    start: int,
    *,
    cigar: tuple[tuple[int, int], ...] = ((0, 128),),
    sa: bool = False,
    supplementary: bool = False,
    paired: bool = True,
    proper: bool = True,
    template_length: int = 350,
    mapq: int = 50,
) -> pysam.AlignedSegment:
    read = pysam.AlignedSegment()
    read.query_name = name
    query_length = sum(length for op, length in cigar if op in {0, 1, 4, 7, 8})
    phase = sum(name.encode()) % 4
    pattern = "ACGT"
    read.query_sequence = "".join(pattern[(phase + index) % 4] for index in range(query_length))
    read.query_qualities = pysam.qualitystring_to_array("I" * query_length)
    read.flag = 0x1 if paired else 0
    if proper:
        read.flag |= 0x2
    if supplementary:
        read.flag |= 0x800
    read.reference_id = 0
    read.reference_start = start
    read.mapping_quality = mapq
    read.cigartuples = cigar
    read.next_reference_id = 0
    read.next_reference_start = start + 300
    read.template_length = template_length
    if sa:
        read.set_tag("SA", "chr1,5000,+,64M64S,60,1;")
    return read


def fetch_reference(chrom: str, start: int, end: int) -> str:
    return "".join("ACGT"[(position ^ (position >> 3)) % 4] for position in range(start, end))


def make_tensors(candidate: Candidate, suffix: str = ""):
    left = [
        fake_read(f"left-ordinary-{suffix}", candidate.del_start0 - 40),
        fake_read(f"left-soft-{suffix}", candidate.del_start0 - 20, cigar=((4, 16), (0, 112))),
        fake_read(f"left-split-{suffix}", candidate.del_start0 - 30, sa=True),
    ]
    right = [
        fake_read(f"right-ordinary-{suffix}", candidate.del_end0 - 40),
        fake_read(f"right-soft-{suffix}", candidate.del_end0 - 20, cigar=((0, 112), (4, 16))),
        fake_read(f"right-disc-{suffix}", candidate.del_end0 - 30, proper=False, template_length=2_000),
    ]
    tensors = extract_example_from_reads(candidate, left, right, fetch_reference)
    if suffix == "neg":
        tensors.read_tokens[0, 0, 0] = 5 if tensors.read_tokens[0, 0, 0] != 5 else 4
    return tensors


def test_normalize_pure_deletion_coordinates():
    assert normalize_pure_deletion(99, "ATTT", "A") == (100, 103)
    assert normalize_pure_deletion(99, "TTTA", "A") == (99, 102)
    with pytest.raises(ValueError, match="delins"):
        normalize_pure_deletion(99, "ATTT", "AG")


def test_assign_person_shards_is_frozen_40_5_5():
    people = {}
    for pop in ("AFR", "AMR", "EAS", "EUR", "SAS"):
        for index in range(10):
            split = "train" if index < 8 else ("val" if index == 8 else "test")
            people[f"{pop}{index}"] = {"super_pop": pop, "split": split}
    shards = assign_person_shards(people)
    assert sum(value == 0 for value in shards.values()) == 5
    assert sum(value == 9 for value in shards.values()) == 5
    assert all(sum(value == shard for value in shards.values()) == 5 for shard in range(1, 9))


def test_negative_matching_tracks_continuous_af_and_is_deterministic():
    sample = "S1"

    def site(index: int, af: float, *, gt: str, length: int, gq: int = 50):
        return {
            "candidate_id": f"c{index:03d}",
            "chrom": f"chr{1 + index % 2}",
            "length": length,
            "length_bucket": "100-199" if length < 200 else "200-499",
            "af": af,
            "af_bucket": "common" if af >= .05 else "rare",
            "repeat_bucket": "annotation_unavailable",
            "qual": 100.0,
            "calls": {sample: {"gt": gt, "gq": gq}},
        }

    positives = [site(i, af, gt="0/1", length=100 + i * 10) for i, af in enumerate((.06, .11, .24, .48))]
    negatives = [
        site(20 + i, af, gt="0/0", length=105 + i * 10)
        for i, af in enumerate((.01, .059, .109, .241, .479, .9))
    ]
    first = select_matched_negatives(negatives, positives, sample, 4)
    second = select_matched_negatives(list(reversed(negatives)), positives, sample, 4)
    assert [row["candidate_id"] for row in first] == [row["candidate_id"] for row in second]
    assert sorted(round(row["af"], 3) for row in first) == [.059, .109, .241, .479]


def test_subset_is_balanced_paired_and_covers_literal_categories():
    samples = ["S1", "S2", "S3", "S4", "S5"]
    rows = []
    lengths = [100, 500, 2500, 150, 700, 3500, 120, 800]
    for index, length in enumerate(lengths):
        positive_sample = samples[index % len(samples)]
        negative_sample = samples[(index + 1) % len(samples)]
        candidate = f"c{index}"
        for sample, label in ((positive_sample, "1"), (negative_sample, "0")):
            rows.append({
                "row_id": f"{candidate}-{sample}-{label}",
                "candidate_id": candidate,
                "sample": sample,
                "label": label,
                "length": str(length),
                "genotype": ("1/1" if index == 1 else "0/1") if label == "1" else "0/0",
            })
    # Add enough paired candidates to fill two examples per class/person.
    for index in range(8, 30):
        positive_sample = samples[index % len(samples)]
        negative_sample = samples[(index + 2) % len(samples)]
        candidate = f"c{index}"
        for sample, label in ((positive_sample, "1"), (negative_sample, "0")):
            rows.append({
                "row_id": f"{candidate}-{sample}-{label}",
                "candidate_id": candidate,
                "sample": sample,
                "label": label,
                "length": "300",
                "genotype": "0/1" if label == "1" else "0/0",
            })
    selected = deterministic_subset(rows, 2)
    assert len(selected) == 20
    assert Counter((row["sample"], row["label"]) for row in selected) == Counter(
        {(sample, label): 2 for sample in samples for label in ("0", "1")}
    )
    assert any(int(row["length"]) <= 200 and row["label"] == "1" for row in selected)
    assert any(200 < int(row["length"]) < 2000 and row["label"] == "1" for row in selected)
    assert any(int(row["length"]) >= 2000 and row["label"] == "1" for row in selected)
    assert any(row["genotype"] == "1/1" for row in selected)


def test_manifest_policy_audit_accepts_strict_rows():
    rows = []
    for index in range(50):
        split = "train" if index < 40 else ("val" if index < 45 else "test")
        shard = 1 + index // 5 if split == "train" else (0 if split == "val" else 9)
        sample = f"S{index:02d}"
        for label in (0, 1):
            rows.append(
                {
                    "row_id": f"r-{index}-{label}",
                    "sample": sample,
                    "candidate_id": "shared-candidate",
                    "split": split,
                    "shard": shard,
                    "label": label,
                    "genotype": "0/1" if label else "0/0",
                    "genotype_quality": 30,
                    "negative_type": "not_applicable" if label else "same_site_negative",
                    "chrom": "chr1",
                    "del_start0": 100,
                    "del_end0": 200,
                    "length": 100,
                    "site_filter": "PASS",
                    "callable_by_genotype": 1,
                    "conflict_free": 1,
                }
            )
    audit = validate_pair_manifest(rows, expected_per_class_per_person=1)
    assert audit["passed"], audit["problems"]
    rows[0]["genotype_quality"] = 19
    assert not validate_pair_manifest(rows, expected_per_class_per_person=1)["passed"]


def test_read_priority_tensor_shapes_and_scalars():
    ordinary = fake_read("ordinary", 950)
    clipped = fake_read("clipped", 950, cigar=((4, 16), (0, 112)))
    split = fake_read("split", 950, sa=True)
    supplementary = fake_read("supp", 950, supplementary=True)
    selected = select_reads([ordinary, clipped, split, supplementary], 1_000, 4)
    assert [selection_reason(read) for read in selected] == [
        "supplementary",
        "split_sa",
        "soft_clipped",
        "ordinary",
    ]
    candidate = Candidate("c1", "chr1", 1_000, 1_200, 200)
    tensors = make_tensors(candidate)
    assert tensors.images.shape == IMAGE_SHAPE
    assert tensors.images.dtype == np.uint8
    assert tensors.read_tokens.shape == READ_TOKEN_SHAPE
    assert tensors.read_mask.shape == READ_MASK_SHAPE
    assert tensors.read_mask.sum() == 6
    assert tensors.scalars.shape == (len(SCALAR_FEATURE_NAMES),)
    assert np.isfinite(tensors.scalars).all()
    assert tensors.scalars[0] > 0 and tensors.scalars[1] > 0


def test_candidate_refalt_is_fixed_and_candidate_dependent():
    candidate = Candidate("c1", "chr1", 1_000, 1_200, 200)
    tokens = build_candidate_refalt_tokens(candidate, fetch_reference)
    assert tokens.shape == (2, 1024)
    assert tokens.dtype == np.uint8
    assert not np.array_equal(tokens[0], tokens[1])


def test_hdf5_roundtrip_failure_flag_and_qc(tmp_path: Path):
    candidate = Candidate("shared", "chr1", 1_000, 1_200, 200)
    h5_path = tmp_path / "shard.h5"
    manifest_path = tmp_path / "manifest.tsv"
    base = {
        "candidate_id": "shared",
        "chrom": "chr1",
        "del_start0": 1_000,
        "del_end0": 1_200,
        "length": 200,
        "split": "val",
        "genotype_quality": 30,
        "negative_type": "same_site_negative",
        "genotype": "0/0",
    }
    with PairSVShardWriter(h5_path, 2, shard_id=0) as writer:
        refalt = build_candidate_refalt_tokens(candidate, fetch_reference)[None, ...]
        writer.write_candidates(["shared"], refalt, np.asarray([[1_000, 1_200]]))
        writer.write_success(
            0,
            {**base, "row_id": "positive", "sample_id": "VAL1", "sample": "VAL1", "label": 1, "genotype": "0/1", "negative_type": "not_applicable"},
            make_tensors(candidate, "pos"),
            0,
        )
        writer.write_success(
            1,
            {**base, "row_id": "negative", "sample_id": "VAL2", "sample": "VAL2", "label": 0},
            make_tensors(candidate, "neg"),
            0,
        )
        writer.write_manifest(manifest_path)
    with h5py.File(h5_path, "r") as h5:
        assert h5["examples/images"].shape == (2,) + IMAGE_SHAPE
        assert h5["examples/success"][:].tolist() == [1, 1]
        assert h5["candidates/refalt_tokens"].shape == (1, 2, 1024)
    report = qc_shard(h5_path, manifest_path)
    assert report["passed"], report["problems"]
    checksum_path = tmp_path / "SHA256SUMS"
    checksums = write_checksums([h5_path, manifest_path], checksum_path)
    assert checksums[h5_path.name] == sha256_file(h5_path)
    assert checksum_path.exists()


def test_failed_candidate_is_explicitly_flagged(tmp_path: Path):
    path = tmp_path / "failed.h5"
    metadata = {
        "row_id": "failed-row",
        "sample_id": "VAL1",
        "candidate_id": "c1",
        "chrom": "chr1",
        "label": 1,
        "del_start0": 100,
        "del_end0": 200,
    }
    with PairSVShardWriter(path, 1, shard_id=0) as writer:
        writer.write_candidates(
            ["c1"],
            np.ones((1, 2, 1024), dtype=np.uint8),
            np.asarray([[100, 200]], dtype=np.int64),
        )
        writer.write_failure(0, metadata, 0, "remote_fetch_exhausted:TimeoutError")
    with h5py.File(path, "r") as h5:
        assert h5["examples/success"][0] == 0
        reason = h5["examples/failure_reason"][0]
        assert "remote_fetch_exhausted" in (reason.decode() if isinstance(reason, bytes) else reason)
        assert h5["examples/images"][0].sum() == 0


def test_training_loader_hides_metadata_and_fits_train_only_scalars(tmp_path: Path):
    candidate = Candidate("shared", "chr1", 1_000, 1_200, 200)
    h5_path = tmp_path / "loader.h5"
    manifest_path = tmp_path / "loader.tsv"
    base = {
        "candidate_id": "shared", "chrom": "chr1", "del_start0": 1_000,
        "del_end0": 1_200, "length": 200, "split": "train",
        "genotype_quality": 30, "negative_type": "same_site_negative", "genotype": "0/0",
    }
    with PairSVShardWriter(h5_path, 2, shard_id=1) as writer:
        writer.write_candidates(["shared"], build_candidate_refalt_tokens(candidate, fetch_reference)[None, ...], np.asarray([[1_000, 1_200]]))
        writer.write_success(0, {**base, "row_id": "p", "sample_id": "TRAIN1", "sample": "TRAIN1", "label": 1, "genotype": "0/1", "negative_type": "not_applicable"}, make_tensors(candidate, "pos"), 0)
        writer.write_success(1, {**base, "row_id": "n", "sample_id": "TRAIN2", "sample": "TRAIN2", "label": 0}, make_tensors(candidate, "neg"), 0)
        writer.write_manifest(manifest_path)
    normalizer = ScalarNormalizer.fit([h5_path])
    dataset = PairSVHDF5Dataset([h5_path], scalar_normalizer=normalizer)
    item = dataset[0]
    assert set(item) == {"images", "read_tokens", "read_mask", "scalars", "refalt_tokens", "label"}
    assert item["images"].shape == IMAGE_SHAPE
    assert item["read_tokens"].shape == READ_TOKEN_SHAPE
    assert item["read_mask"].shape == READ_MASK_SHAPE
    assert item["refalt_tokens"].shape == (2, 1024)
    assert np.isfinite(item["scalars"]).all()
    dataset.close()


def test_refalt_token_decoder_preserves_candidate_sequence_contract():
    tokens = np.asarray([1, 2, 3, 4, 5] + [0] * 1019, dtype=np.uint8)
    decoded = tokens_to_sequence(tokens)
    assert decoded[:6] == "ACGTNN"
    assert len(decoded) == 1024

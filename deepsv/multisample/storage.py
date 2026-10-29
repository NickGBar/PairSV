"""Versioned, chunked HDF5 storage for production PAIR-SV shards."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

import h5py
import numpy as np

from .extraction import (
    IMAGE_SHAPE,
    READ_MASK_SHAPE,
    READ_TOKEN_SHAPE,
    SCALAR_FEATURE_NAMES,
    ExampleTensors,
)


SHARD_SCHEMA_VERSION = "pairsv-shard-v1"
MODEL_TENSOR_DATASETS = (
    "examples/images",
    "examples/read_tokens",
    "examples/read_mask",
    "examples/scalars",
    "candidates/refalt_tokens",
)


def sha256_file(path: str | Path, block_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


class PairSVShardWriter:
    """Preallocated writer; failed rows remain zero only with success=0 + reason."""

    def __init__(self, path: str | Path, n_rows: int, *, shard_id: int) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.n_rows = int(n_rows)
        self.file = h5py.File(self.path, "w")
        self.file.attrs.update(
            {
                "schema_version": SHARD_SCHEMA_VERSION,
                "shard_id": int(shard_id),
                "scalar_feature_names": json.dumps(SCALAR_FEATURE_NAMES),
                "model_tensor_datasets": json.dumps(MODEL_TENSOR_DATASETS),
            }
        )
        examples = self.file.create_group("examples")
        compression = {"compression": "gzip", "compression_opts": 1, "shuffle": True}
        examples.create_dataset(
            "images",
            shape=(n_rows,) + IMAGE_SHAPE,
            dtype="u1",
            chunks=(1,) + IMAGE_SHAPE,
            **compression,
        )
        examples.create_dataset(
            "read_tokens",
            shape=(n_rows,) + READ_TOKEN_SHAPE,
            dtype="u1",
            chunks=(min(4, max(1, n_rows)),) + READ_TOKEN_SHAPE,
            **compression,
        )
        examples.create_dataset(
            "read_mask",
            shape=(n_rows,) + READ_MASK_SHAPE,
            dtype="u1",
            chunks=(min(128, max(1, n_rows)),) + READ_MASK_SHAPE,
            **compression,
        )
        examples.create_dataset(
            "scalars",
            shape=(n_rows, len(SCALAR_FEATURE_NAMES)),
            dtype="f4",
            chunks=(min(256, max(1, n_rows)), len(SCALAR_FEATURE_NAMES)),
            **compression,
        )
        examples.create_dataset("label", shape=(n_rows,), dtype="u1")
        examples.create_dataset("candidate_index", shape=(n_rows,), dtype="i4", fillvalue=-1)
        examples.create_dataset("success", shape=(n_rows,), dtype="u1")
        string = h5py.string_dtype("utf-8")
        for name in ("row_id", "sample_id", "candidate_id", "chrom", "failure_reason"):
            examples.create_dataset(name, shape=(n_rows,), dtype=string)
        examples.create_dataset("breakpoints", shape=(n_rows, 2), dtype="i8")

        metadata = self.file.create_group("read_metadata")
        metadata.create_dataset(
            "cigar", shape=(n_rows,) + READ_MASK_SHAPE, dtype="S64", chunks=(min(16, max(1, n_rows)),) + READ_MASK_SHAPE, **compression
        )
        for name, dtype in (
            ("strand", "i1"),
            ("mapq", "u1"),
            ("supplementary", "u1"),
            ("selection_reason", "u1"),
        ):
            metadata.create_dataset(name, shape=(n_rows,) + READ_MASK_SHAPE, dtype=dtype, chunks=(min(64, max(1, n_rows)),) + READ_MASK_SHAPE, **compression)
        metadata.create_dataset("mean_base_quality", shape=(n_rows,) + READ_MASK_SHAPE, dtype="f4", chunks=(min(64, max(1, n_rows)),) + READ_MASK_SHAPE, **compression)
        metadata.create_dataset("read_name_hash", shape=(n_rows,) + READ_MASK_SHAPE, dtype="S16", chunks=(min(64, max(1, n_rows)),) + READ_MASK_SHAPE, **compression)
        self.manifest_rows: list[dict[str, object]] = []

    def write_candidates(
        self,
        candidate_ids: Sequence[str],
        refalt_tokens: np.ndarray,
        coordinates: np.ndarray,
    ) -> None:
        if refalt_tokens.shape != (len(candidate_ids), 2, 1024):
            raise ValueError(f"unexpected REF/ALT tensor shape {refalt_tokens.shape}")
        group = self.file.create_group("candidates")
        group.create_dataset("candidate_id", data=np.asarray(candidate_ids, dtype=object), dtype=h5py.string_dtype("utf-8"))
        group.create_dataset(
            "refalt_tokens",
            data=refalt_tokens.astype(np.uint8, copy=False),
            chunks=(min(64, max(1, len(candidate_ids))), 2, 1024),
            compression="gzip",
            compression_opts=1,
            shuffle=True,
        )
        group.create_dataset("coordinates", data=np.asarray(coordinates, dtype=np.int64))

    def write_success(
        self,
        index: int,
        metadata: Mapping[str, object],
        tensors: ExampleTensors,
        candidate_index: int,
    ) -> None:
        self._write_common(index, metadata, candidate_index, success=True, failure_reason="")
        examples = self.file["examples"]
        examples["images"][index] = tensors.images
        examples["read_tokens"][index] = tensors.read_tokens
        examples["read_mask"][index] = tensors.read_mask
        examples["scalars"][index] = tensors.scalars
        read_meta = self.file["read_metadata"]
        read_meta["cigar"][index] = tensors.read_cigar
        read_meta["strand"][index] = tensors.read_strand
        read_meta["mapq"][index] = tensors.read_mapq
        read_meta["mean_base_quality"][index] = tensors.read_mean_bq
        read_meta["supplementary"][index] = tensors.read_supplementary
        read_meta["read_name_hash"][index] = tensors.read_name_hash
        read_meta["selection_reason"][index] = tensors.read_selection_reason

    def write_failure(
        self,
        index: int,
        metadata: Mapping[str, object],
        candidate_index: int,
        failure_reason: str,
    ) -> None:
        self._write_common(index, metadata, candidate_index, success=False, failure_reason=failure_reason)

    def _write_common(
        self,
        index: int,
        metadata: Mapping[str, object],
        candidate_index: int,
        *,
        success: bool,
        failure_reason: str,
    ) -> None:
        if not 0 <= index < self.n_rows:
            raise IndexError(index)
        examples = self.file["examples"]
        for field in ("row_id", "sample_id", "candidate_id", "chrom"):
            examples[field][index] = str(metadata[field])
        examples["label"][index] = int(metadata["label"])
        examples["candidate_index"][index] = int(candidate_index)
        examples["success"][index] = int(success)
        examples["failure_reason"][index] = str(failure_reason)[:500]
        examples["breakpoints"][index] = [int(metadata["del_start0"]), int(metadata["del_end0"])]
        self.manifest_rows.append(
            {
                **{key: metadata[key] for key in metadata},
                "candidate_index": candidate_index,
                "extraction_success": int(success),
                "failure_reason": failure_reason,
            }
        )

    def close(self) -> None:
        if self.file:
            self.file.flush()
            self.file.close()
            self.file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def write_manifest(self, path: str | Path) -> None:
        if not self.manifest_rows:
            raise ValueError("cannot write an empty shard manifest")
        fields = list(self.manifest_rows[0])
        with Path(path).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self.manifest_rows)


def write_checksums(paths: Sequence[str | Path], output_path: str | Path) -> dict[str, str]:
    checksums = {str(Path(path).name): sha256_file(path) for path in paths}
    with Path(output_path).open("w") as handle:
        for name, checksum in sorted(checksums.items()):
            handle.write(f"{checksum}  {name}\n")
    return checksums

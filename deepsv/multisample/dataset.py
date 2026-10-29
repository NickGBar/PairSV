"""Leakage-safe HDF5 reader for PAIR-SV CNN and fusion training."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np

from .storage import MODEL_TENSOR_DATASETS, SHARD_SCHEMA_VERSION


@dataclass(frozen=True)
class ScalarNormalizer:
    """Train-only scalar normalization parameters."""

    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def fit(cls, shard_paths: list[str | Path]) -> "ScalarNormalizer":
        total = None
        total_sq = None
        count = 0
        for path in shard_paths:
            with h5py.File(path, "r") as h5:
                _validate_h5_schema(h5)
                success = h5["examples/success"][:].astype(bool)
                values = h5["examples/scalars"][success].astype(np.float64)
                if not len(values):
                    continue
                total = values.sum(axis=0) if total is None else total + values.sum(axis=0)
                total_sq = (values * values).sum(axis=0) if total_sq is None else total_sq + (values * values).sum(axis=0)
                count += len(values)
        if count == 0:
            raise ValueError("cannot fit scalar normalization without successful train examples")
        mean = total / count
        variance = np.maximum(total_sq / count - mean * mean, 1e-12)
        return cls(mean.astype(np.float32), np.sqrt(variance).astype(np.float32))

    def transform(self, values: np.ndarray) -> np.ndarray:
        return ((values.astype(np.float32) - self.mean) / self.std).astype(np.float32, copy=False)


def _validate_h5_schema(h5: h5py.File) -> None:
    if h5.attrs.get("schema_version", "") != SHARD_SCHEMA_VERSION:
        raise ValueError(f"unexpected PAIR-SV shard schema {h5.attrs.get('schema_version')!r}")
    fields = tuple(json.loads(h5.attrs["model_tensor_datasets"]))
    if fields != MODEL_TENSOR_DATASETS:
        raise ValueError("HDF5 model tensor whitelist differs from PAIR-SV schema")


class PairSVHDF5Dataset:
    """Worker-safe, success-only reader exposing no identity/QC metadata.

    The returned dictionaries contain only training tensors: paired images,
    selected read tokens/masks, 17 scalar features, candidate REF/ALT tokens,
    and the label. ``sample_id``, population, split, GQ, negative type,
    source filename, coordinates, read names, and failure text are never
    returned by this interface.
    """

    def __init__(
        self,
        shard_paths: list[str | Path],
        *,
        scalar_normalizer: ScalarNormalizer | None = None,
    ) -> None:
        self.paths = [str(Path(path)) for path in shard_paths]
        self.scalar_normalizer = scalar_normalizer
        self.index: list[tuple[int, int]] = []
        self._handles: dict[int, h5py.File] = {}
        for shard_index, path in enumerate(self.paths):
            with h5py.File(path, "r") as h5:
                _validate_h5_schema(h5)
                for row_index in np.flatnonzero(h5["examples/success"][:]):
                    self.index.append((shard_index, int(row_index)))
        if not self.index:
            raise ValueError("no successful PAIR-SV examples across supplied shards")

    def __len__(self) -> int:
        return len(self.index)

    def _handle(self, shard_index: int) -> h5py.File:
        handle = self._handles.get(shard_index)
        if handle is None or not handle.id.valid:
            handle = h5py.File(self.paths[shard_index], "r")
            _validate_h5_schema(handle)
            self._handles[shard_index] = handle
        return handle

    def __getitem__(self, index: int) -> dict[str, np.ndarray | np.uint8]:
        shard_index, row_index = self.index[index]
        h5 = self._handle(shard_index)
        examples = h5["examples"]
        scalar = examples["scalars"][row_index].astype(np.float32, copy=False)
        if self.scalar_normalizer is not None:
            scalar = self.scalar_normalizer.transform(scalar)
        candidate_index = int(examples["candidate_index"][row_index])
        return {
            "images": examples["images"][row_index].astype(np.float32) / 255.0,
            "read_tokens": examples["read_tokens"][row_index].astype(np.uint8, copy=False),
            "read_mask": examples["read_mask"][row_index].astype(np.uint8, copy=False),
            "scalars": scalar,
            "refalt_tokens": h5["candidates/refalt_tokens"][candidate_index].astype(np.uint8, copy=False),
            "label": np.uint8(examples["label"][row_index]),
        }

    def close(self) -> None:
        for handle in self._handles.values():
            if handle.id.valid:
                handle.close()
        self._handles.clear()

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_handles"] = {}
        return state

    def __del__(self):
        self.close()

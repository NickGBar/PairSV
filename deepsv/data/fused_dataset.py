"""Image + HyenaDNA-embedding dataset for FiLM-conditioned DeepSV training.

Extends the path-based :class:`deepsv.training.trainer.ImageDataset` with a
second modality: a 256-dim HyenaDNA embedding looked up by ``(chrom,
window_idx)`` from a precomputed HDF5 file (see
``scripts/precompute_hyenadna_embeddings.py``).

Embedding lookup is::

    window_idx = position // window_size       # window_size from H5 attrs
    emb = embeddings[chrom][window_idx]        # (embed_dim,) float16

Per the project spec, the H5 file is opened read-only and entire chromosome
arrays for the requested chroms are pre-loaded into a RAM dict at dataset
init. The chr20–22 cache (~1.5 GB at 256 dim × 50 bp × ~150 Mb / chrom) fits
in T4 GPU host RAM and avoids per-batch HDF5 reads. Embeddings are cast
from ``float16`` → ``float32`` before being returned.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import h5py
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)


class _SparseWindowArray:
    """RAM-compact stand-in for a dense ``(n_windows, embed_dim)`` array.

    Only the window rows actually requested by the dataset (target windows plus
    their ``context_radius`` neighbours) are held in memory; every other row
    reads back as zeros. It supports exactly the two access patterns the
    lookup methods use — integer indexing ``arr[i]`` and contiguous slicing
    ``arr[start:end]`` — and exposes ``.shape``, so callers cannot tell it
    apart from a real ``np.ndarray``. This lets genome-wide splits (chr1–18
    would be ~26 GB as dense float16) fit in RAM without changing the
    coordinate convention (``window_idx = position // window_size``) or the
    lookup code by even one line.
    """

    def __init__(self, rows: Dict[int, np.ndarray], n_windows: int, embed_dim: int):
        self._rows = rows
        self.shape = (int(n_windows), int(embed_dim))
        self._embed_dim = int(embed_dim)
        self.dtype = np.float16
        self.nbytes = sum(r.nbytes for r in rows.values())

    def __getitem__(self, key):
        if isinstance(key, (int, np.integer)):
            row = self._rows.get(int(key))
            if row is None:
                return np.zeros(self._embed_dim, dtype=np.float16)
            return row
        if isinstance(key, slice):
            start, stop, step = key.indices(self.shape[0])
            idxs = range(start, stop, step)
            out = np.zeros((len(idxs), self._embed_dim), dtype=np.float16)
            for j, wi in enumerate(idxs):
                row = self._rows.get(wi)
                if row is not None:
                    out[j] = row
            return out
        raise TypeError(f"_SparseWindowArray supports int/slice indexing, got {type(key)}")


def _resolve_chrom_key(h5_keys: Sequence[str], chrom: str) -> str:
    """Resolve a chromosome name to whatever key style the H5 file uses.

    Some pipelines write ``"chr1"`` keys, others write ``"1"``. Accept both
    on input and translate to whichever the file actually contains.
    """
    if chrom in h5_keys:
        return chrom
    if chrom.startswith("chr") and chrom[3:] in h5_keys:
        return chrom[3:]
    if not chrom.startswith("chr") and f"chr{chrom}" in h5_keys:
        return f"chr{chrom}"
    raise KeyError(
        f"Chromosome {chrom!r} not found in HDF5 file. Available keys: "
        f"{sorted(h5_keys)}"
    )


def _read_window_size(h5_file: h5py.File) -> int:
    """Read the per-window bp size from H5 attrs.

    The spec example uses ``attrs/window_size`` while the actual producer
    (``precompute_hyenadna_embeddings.py``) uses ``window_bp`` at the
    file root. Accept both.
    """
    if "window_bp" in h5_file.attrs:
        return int(h5_file.attrs["window_bp"])
    if "window_size" in h5_file.attrs:
        return int(h5_file.attrs["window_size"])
    if "attrs" in h5_file and isinstance(h5_file["attrs"], h5py.Group):
        attrs_group = h5_file["attrs"]
        if "window_size" in attrs_group.attrs:
            return int(attrs_group.attrs["window_size"])
        if "window_bp" in attrs_group.attrs:
            return int(attrs_group.attrs["window_bp"])
    raise KeyError(
        "HDF5 embeddings file is missing 'window_bp' / 'window_size' attrs; "
        "cannot determine genomic window size."
    )


def _read_embed_dim(h5_file: h5py.File, sample_chrom_key: str) -> int:
    """Read embed_dim from attrs, falling back to the first dataset's shape."""
    if "embed_dim" in h5_file.attrs:
        return int(h5_file.attrs["embed_dim"])
    if "attrs" in h5_file and isinstance(h5_file["attrs"], h5py.Group):
        if "embed_dim" in h5_file["attrs"].attrs:
            return int(h5_file["attrs"].attrs["embed_dim"])
    return int(h5_file[sample_chrom_key].shape[1])


class FusedDataset(Dataset):
    """Dataset returning ``(image, embedding, label)`` triples.

    Args:
        image_paths: List of pileup-image file paths.
        labels: List of integer labels (0 = non-deletion, 1 = deletion).
        chroms: Per-sample chromosome name (e.g. ``"chr21"`` or ``"21"``).
        positions: Per-sample 0-based genomic position used to derive the
            window index. Should be the *centre* of the 50 bp window the
            image was rendered from.
        embeddings_h5: Path to the HDF5 file written by
            ``scripts/precompute_hyenadna_embeddings.py``.
        preload_chroms: Optional list of chromosomes to pre-load into RAM
            at init. If ``None``, the union of unique values in ``chroms``
            is used.
        transform: Optional torchvision-style image transform.
        embed_dtype: dtype of returned embeddings. Defaults to float32.
    """

    def __init__(
        self,
        image_paths: List[str],
        labels: List[int],
        chroms: List[str],
        positions: List[int],
        embeddings_h5: str,
        preload_chroms: Optional[Sequence[str]] = None,
        transform=None,
        embed_dtype: torch.dtype = torch.float32,
        context_radius: int = 0,
    ) -> None:
        """Args (new):
        context_radius: If 0 (default), ``__getitem__`` returns a single
            ``(embed_dim,)`` embedding for the target window — unchanged
            behaviour for FiLM / context-calibration fusion. If > 0, returns
            a ``(2*context_radius+1, embed_dim)`` sequence of the target
            window's embedding plus its ``context_radius`` neighbours on each
            side — for cross-attention fusion, where the CNN's spatial
            columns attend over this token sequence. Edge windows are padded
            by repeating the boundary row, matching
            ``SequencePriorDataset``'s windowing convention.
        """
        n = len(image_paths)
        if not (len(labels) == len(chroms) == len(positions) == n):
            raise ValueError(
                "image_paths, labels, chroms and positions must all have the "
                f"same length; got {n}, {len(labels)}, {len(chroms)}, "
                f"{len(positions)}."
            )

        self.image_paths = image_paths
        self.labels = labels
        self.chroms = chroms
        self.positions = positions
        self.transform = transform
        self.embed_dtype = embed_dtype
        self.embeddings_h5 = str(embeddings_h5)
        if context_radius < 0:
            raise ValueError(f"context_radius must be >= 0; got {context_radius}")
        self.context_radius = int(context_radius)

        chroms_to_load = (
            list(dict.fromkeys(preload_chroms))
            if preload_chroms is not None
            else list(dict.fromkeys(chroms))
        )
        if not chroms_to_load:
            raise ValueError(
                "FusedDataset requires at least one chromosome to load "
                "embeddings for; got an empty list."
            )

        logger.info(
            "Loading HyenaDNA embeddings from %s (chroms=%s) …",
            self.embeddings_h5,
            chroms_to_load,
        )

        self._embeddings: Dict[str, np.ndarray] = {}
        with h5py.File(self.embeddings_h5, "r") as f:
            self.window_size = _read_window_size(f)
            sample_key = _resolve_chrom_key(list(f.keys()), chroms_to_load[0])
            self.embed_dim = _read_embed_dim(f, sample_key)

            # Which window rows will actually be requested per chromosome?
            # Target window is position // window_size; cross-attention also
            # reads context_radius neighbours on each side (clamped to the
            # chromosome). Everything else can stay out of RAM.
            needed: Dict[str, set] = {c: set() for c in chroms_to_load}
            for c, pos in zip(self.chroms, self.positions):
                if c not in needed:
                    continue
                center = int(pos) // self.window_size
                for wi in range(center - self.context_radius,
                                 center + self.context_radius + 1):
                    if wi >= 0:
                        needed[c].add(wi)

            self._chrom_key_map: Dict[str, str] = {}
            file_keys = list(f.keys())
            for chrom in chroms_to_load:
                key = _resolve_chrom_key(file_keys, chrom)
                self._chrom_key_map[chrom] = key
                dset = f[key]
                n_windows = int(dset.shape[0])
                idxs = sorted(wi for wi in needed[chrom] if wi < n_windows)
                if idxs:
                    block = dset[idxs]  # h5py fancy read: only these rows
                    rows = {wi: block[j] for j, wi in enumerate(idxs)}
                else:
                    rows = {}
                arr = _SparseWindowArray(rows, n_windows, self.embed_dim)
                self._embeddings[chrom] = arr
                logger.info(
                    "  %s → key=%s  shape=%s  cached_rows=%d  size=%.2f MB",
                    chrom,
                    key,
                    arr.shape,
                    len(rows),
                    arr.nbytes / 1e6,
                )

        unknown = [c for c in chroms if c not in self._embeddings]
        if unknown:
            raise ValueError(
                f"Sample chroms include {sorted(set(unknown))} but embeddings "
                f"are only loaded for {sorted(self._embeddings)}. Pass them "
                "via ``preload_chroms``."
            )

    def __len__(self) -> int:
        return len(self.image_paths)

    # ------------------------------------------------------------------
    # Embedding lookup
    # ------------------------------------------------------------------

    def lookup_embedding(self, chrom: str, position: int) -> np.ndarray:
        """Fetch the embedding for ``(chrom, position)`` from the RAM cache.

        Args:
            chrom: Chromosome name as used at construction time.
            position: 0-based genomic position. The window index is
                ``position // window_size``.

        Returns:
            ``(embed_dim,)`` ``np.float32`` array.
        """
        if chrom not in self._embeddings:
            raise KeyError(
                f"No embeddings preloaded for {chrom!r}; available: "
                f"{sorted(self._embeddings)}"
            )
        arr = self._embeddings[chrom]
        window_idx = int(position) // self.window_size
        if window_idx < 0 or window_idx >= arr.shape[0]:
            raise IndexError(
                f"window_idx={window_idx} out of range for {chrom} "
                f"(n_windows={arr.shape[0]}); position={position}, "
                f"window_size={self.window_size}."
            )
        return arr[window_idx].astype(np.float32, copy=False)

    def lookup_context_embeddings(self, chrom: str, position: int) -> np.ndarray:
        """Fetch ``2*context_radius+1`` neighbouring window embeddings.

        Centred on the target window, ordered upstream → target → downstream.
        Out-of-range neighbours (near a chromosome edge) are filled by
        repeating the boundary row, so the returned array always has shape
        ``(2*context_radius+1, embed_dim)``.
        """
        if chrom not in self._embeddings:
            raise KeyError(
                f"No embeddings preloaded for {chrom!r}; available: "
                f"{sorted(self._embeddings)}"
            )
        arr = self._embeddings[chrom]
        n_windows = int(arr.shape[0])
        center = int(position) // self.window_size
        center = min(max(center, 0), n_windows - 1)
        raw_start = center - self.context_radius
        raw_end = center + self.context_radius + 1
        start = max(0, raw_start)
        end = min(n_windows, raw_end)
        x_np = arr[start:end].astype(np.float32, copy=False)
        left_pad = max(0, -raw_start)
        right_pad = max(0, raw_end - n_windows)
        if left_pad:
            x_np = np.concatenate((np.repeat(x_np[:1], left_pad, axis=0), x_np), axis=0)
        if right_pad:
            x_np = np.concatenate((x_np, np.repeat(x_np[-1:], right_pad, axis=0)), axis=0)
        return x_np

    # ------------------------------------------------------------------
    # Dataset protocol
    # ------------------------------------------------------------------

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, int]:
        image = Image.open(self.image_paths[idx]).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)

        chrom = self.chroms[idx]
        position = self.positions[idx]
        if self.context_radius > 0:
            emb_np = self.lookup_context_embeddings(chrom, position)
        else:
            emb_np = self.lookup_embedding(chrom, position)
        embedding = torch.from_numpy(emb_np).to(self.embed_dtype)

        return image, embedding, int(self.labels[idx])

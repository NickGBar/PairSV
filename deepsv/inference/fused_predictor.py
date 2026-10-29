"""Inference for FusedDeepSV / CrossAttnDeepSV (image + frozen embedding).

Mirror of :class:`deepsv.inference.predictor.DeletionPredictor` but for the
two-modality fused models. Embeddings are read from the same HDF5 layout
produced by ``scripts/precompute_hyenadna_embeddings.py``: ``(chrom,
position)`` → ``embeddings[chrom][position // window_size]``.

The H5 file is opened on construction and held read-only for the predictor's
lifetime. Per-call lookups are O(1) array indexes; embeddings are cast from
``float16`` → ``float32`` before entering the model.

With ``context_radius=0`` (default), returns a single ``(embed_dim,)``
embedding per sample — for :class:`FusedDeepSV` (FiLM / context calibration).
With ``context_radius>0``, returns a ``(2*context_radius+1, embed_dim)``
window sequence — for :class:`CrossAttnDeepSV`. This mirrors
:class:`~deepsv.data.fused_dataset.FusedDataset`'s ``context_radius`` exactly
(same edge-padding convention), since inference must see the same embedding
shape training did.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import h5py
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image

from ..data.fused_dataset import _read_embed_dim, _read_window_size, _resolve_chrom_key
from ..models.cross_attn_cnn import CrossAttnDeepSV
from ..models.fused_cnn import FusedDeepSV

logger = logging.getLogger(__name__)


class FusedPredictor:
    """Inference handler for :class:`FusedDeepSV` or :class:`CrossAttnDeepSV`.

    Args:
        model: A trained :class:`FusedDeepSV` or :class:`CrossAttnDeepSV`.
        embeddings_h5: Path to the precomputed HyenaDNA HDF5 file.
        device: Inference device. Defaults to CUDA if available.
        threshold: Probability threshold for the positive class.
        preload_chroms: Optional list of chromosomes to load into RAM.
            If ``None``, embeddings are read lazily from disk per-call.
        context_radius: Must match the ``context_radius`` the model's
            checkpoint was trained with. ``0`` (default) for
            :class:`FusedDeepSV`; the same positive integer used at training
            time for :class:`CrossAttnDeepSV`.
    """

    def __init__(
        self,
        model: Union[FusedDeepSV, CrossAttnDeepSV],
        embeddings_h5: str,
        device: Optional[torch.device] = None,
        threshold: float = 0.5,
        preload_chroms: Optional[Sequence[str]] = None,
        context_radius: int = 0,
    ) -> None:
        self.model = model
        if context_radius < 0:
            raise ValueError(f"context_radius must be >= 0; got {context_radius}")
        self.context_radius = int(context_radius)
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model.to(self.device).eval()
        self.threshold = threshold
        self.embeddings_h5 = str(embeddings_h5)

        self.transform = transforms.Compose(
            [
                transforms.Resize((256, 256)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]
                ),
            ]
        )

        # Open H5 to read attrs and (optionally) preload chrom arrays.
        self._h5: Optional[h5py.File] = h5py.File(self.embeddings_h5, "r")
        self.window_size = _read_window_size(self._h5)
        sample_key = next(iter(self._h5.keys()))
        self.embed_dim = _read_embed_dim(self._h5, sample_key)

        self._cache: Dict[str, np.ndarray] = {}
        self._chrom_key_map: Dict[str, str] = {}
        if preload_chroms:
            file_keys = list(self._h5.keys())
            for chrom in preload_chroms:
                key = _resolve_chrom_key(file_keys, chrom)
                self._chrom_key_map[chrom] = key
                self._cache[chrom] = self._h5[key][:]
                logger.info(
                    "Preloaded %s (key=%s) shape=%s", chrom, key, self._cache[chrom].shape
                )

    def close(self) -> None:
        """Release the HDF5 handle."""
        if self._h5 is not None:
            self._h5.close()
            self._h5 = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------
    # Embedding lookup
    # ------------------------------------------------------------------

    def _array_for_chrom(self, chrom: str):
        """Return the embedding array/dataset for ``chrom`` (cached numpy
        array if preloaded, else the live HDF5 dataset — both slice the
        same way, so callers don't need to care which)."""
        if chrom in self._cache:
            return self._cache[chrom]
        if self._h5 is None:
            raise RuntimeError("FusedPredictor: HDF5 file is closed.")
        if chrom not in self._chrom_key_map:
            self._chrom_key_map[chrom] = _resolve_chrom_key(
                list(self._h5.keys()), chrom
            )
        return self._h5[self._chrom_key_map[chrom]]

    def _get_embedding(self, chrom: str, position: int) -> np.ndarray:
        arr = self._array_for_chrom(chrom)
        window_idx = int(position) // self.window_size
        n_windows = int(arr.shape[0])
        if window_idx < 0 or window_idx >= n_windows:
            raise IndexError(
                f"window_idx={window_idx} out of range for {chrom} "
                f"(n_windows={n_windows}); position={position}, "
                f"window_size={self.window_size}."
            )
        return np.asarray(arr[window_idx], dtype=np.float32)

    def _get_context_embeddings(self, chrom: str, position: int) -> np.ndarray:
        """Fetch ``2*context_radius+1`` neighbouring window embeddings,
        centred on the target window. Mirrors
        ``FusedDataset.lookup_context_embeddings`` exactly — same
        edge-padding convention (repeat the boundary row), since the model
        was trained on that convention and inference must match it."""
        arr = self._array_for_chrom(chrom)
        n_windows = int(arr.shape[0])
        center = int(position) // self.window_size
        center = min(max(center, 0), n_windows - 1)
        raw_start = center - self.context_radius
        raw_end = center + self.context_radius + 1
        start = max(0, raw_start)
        end = min(n_windows, raw_end)
        x_np = np.asarray(arr[start:end], dtype=np.float32)
        left_pad = max(0, -raw_start)
        right_pad = max(0, raw_end - n_windows)
        if left_pad:
            x_np = np.concatenate((np.repeat(x_np[:1], left_pad, axis=0), x_np), axis=0)
        if right_pad:
            x_np = np.concatenate((x_np, np.repeat(x_np[-1:], right_pad, axis=0)), axis=0)
        return x_np

    def _lookup(self, chrom: str, position: int) -> np.ndarray:
        """Dispatch to single-vector or context-window lookup as configured."""
        if self.context_radius > 0:
            return self._get_context_embeddings(chrom, position)
        return self._get_embedding(chrom, position)

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    @torch.no_grad()
    def predict(
        self, image_path: Path, chrom: str, position: int
    ) -> Tuple[float, int]:
        """Predict deletion probability for one ``(image, chrom, position)``.

        Returns:
            ``(prob_deletion, predicted_class)``.
        """
        image = Image.open(image_path).convert("RGB")
        image_tensor = self.transform(image).unsqueeze(0).to(self.device)

        emb_np = self._lookup(chrom, position)
        emb_tensor = torch.from_numpy(emb_np).unsqueeze(0).to(self.device).float()

        outputs = self.model(image_tensor, emb_tensor)
        probs = torch.softmax(outputs, dim=1)
        prob_del = probs[0, 1].item()
        predicted = 1 if prob_del > self.threshold else 0
        return prob_del, predicted

    @torch.no_grad()
    def predict_batch(
        self,
        image_paths: List[Path],
        chroms: List[str],
        positions: List[int],
        batch_size: int = 64,
    ) -> List[Tuple[float, int]]:
        """Batched prediction over aligned lists of paths / chroms / positions."""
        n = len(image_paths)
        if not (len(chroms) == len(positions) == n):
            raise ValueError(
                "image_paths, chroms and positions must be the same length; "
                f"got {n}, {len(chroms)}, {len(positions)}."
            )

        # Pre-allocate one slot per input. Failed items keep the (0.0, 0)
        # sentinel; successes are filled in after the batched forward pass.
        # This preserves index alignment with the input lists.
        results: List[Tuple[float, int]] = [(0.0, 0)] * n

        for start in range(0, n, batch_size):
            end = min(n, start + batch_size)
            valid_imgs: List[torch.Tensor] = []
            valid_embs: List[np.ndarray] = []
            valid_indices: List[int] = []

            for i in range(start, end):
                try:
                    img = Image.open(image_paths[i]).convert("RGB")
                    valid_imgs.append(self.transform(img))
                    valid_embs.append(self._lookup(chroms[i], positions[i]))
                    valid_indices.append(i)
                except Exception as e:
                    logger.error(
                        "Error preparing sample %s (chrom=%s pos=%s): %s",
                        image_paths[i], chroms[i], positions[i], e,
                    )
                    # results[i] stays (0.0, 0) by initialisation.

            if not valid_indices:
                continue

            img_batch = torch.stack(valid_imgs).to(self.device)
            emb_batch = torch.from_numpy(np.stack(valid_embs)).to(self.device).float()

            outputs = self.model(img_batch, emb_batch)
            probs = torch.softmax(outputs, dim=1)[:, 1].cpu().tolist()
            for idx, prob in zip(valid_indices, probs):
                results[idx] = (prob, 1 if prob > self.threshold else 0)

        return results

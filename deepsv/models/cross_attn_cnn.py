"""Cross-attention fusion of the DeepSV image CNN with a frozen
sequence-embedding context window (e.g. HyenaDNA-small).

:class:`CrossAttnDeepSV` — CNN spatial *columns* (the genomic-position axis
the classifier head already preserves via its avg/max-pool-over-reads trick,
see :meth:`ModernDeletionCNN._classifier_features`) attend, as queries, over
a sequence of neighbouring 50 bp window embeddings (keys/values) supplied by
:class:`~deepsv.data.fused_dataset.FusedDataset` with ``context_radius > 0``.

This is the piece FiLM and late context calibration don't have: those two
fuse a single pooled embedding per target window, so a false-positive-prone
window and the repeat element three windows upstream that actually explains
it look identical to the model. Cross-attention lets each spatial column
pick which neighbouring window is relevant, instead of pre-averaging that
decision away at precompute time.

Like FiLM and context calibration, the attention output is injected through
a zero-initialised projection, so at step 0 the model is an exact identity
wrapper around the image-only CNN: attention contributes nothing until it
learns to.
"""

from __future__ import annotations

from typing import Optional, Sequence

import torch
import torch.nn as nn

from .cnn import ModernDeletionCNN

# Spatial width (the genomic-position axis) at each hook point for a
# 256x256 input, after 4x stride-2 max pools total (2 before hook3, 1 more
# before hook4). Channel counts must match cnn.py's block definitions.
_HOOK_CHANNELS = {
    "hook3": ModernDeletionCNN.BLOCK3_CHANNELS,  # 96 channels, W=32
    "hook4": ModernDeletionCNN.BLOCK4_CHANNELS,  # 96 channels, W=16
}
_VALID_HOOKS = tuple(_HOOK_CHANNELS)


class _RelativePositionEmbedding(nn.Module):
    """Learned embedding for a context token's offset from the target window.

    Offsets run upstream → target → downstream (index 0 = most upstream,
    index ``context_radius`` = the target window itself). Zero-initialised
    so position carries no bias until training adds one.
    """

    def __init__(self, context_radius: int, dim: int) -> None:
        super().__init__()
        self.n_tokens = 2 * context_radius + 1
        self.table = nn.Embedding(self.n_tokens, dim)
        nn.init.zeros_(self.table.weight)

    def forward(self, batch_size: int, device: torch.device) -> torch.Tensor:
        idx = torch.arange(self.n_tokens, device=device)
        return self.table(idx).unsqueeze(0).expand(batch_size, -1, -1)


class WindowCrossAttention(nn.Module):
    """CNN spatial columns (Q) attend over a context-window token sequence (K,V).

    Q: one token per feature-map column, built the same way the CNN's own
       classifier summarises the read axis — ``concat(avg_H, max_H)``.
    K,V: the ``(2*context_radius+1, embed_dim)`` sequence of neighbouring
       window embeddings for this sample (see ``FusedDataset.context_radius``).

    The output projection is zero-initialised: whatever the attention
    computes internally, its contribution back into the CNN feature map is
    exactly 0 at step 0 — the same identity-at-init discipline used by
    :class:`~deepsv.models.film.FiLMGenerator` and the late
    context-calibration heads in :class:`~deepsv.models.fused_cnn.FusedDeepSV`.
    """

    def __init__(
        self,
        cnn_channels: int,
        embed_dim: int,
        context_radius: int,
        d_model: int = 128,
        n_heads: int = 4,
        dropout_rate: float = 0.1,
    ) -> None:
        super().__init__()
        self.cnn_channels = cnn_channels
        self.d_model = d_model

        self.q_proj = nn.Linear(2 * cnn_channels, d_model)
        self.k_proj = nn.Linear(embed_dim, d_model)
        self.v_proj = nn.Linear(embed_dim, d_model)
        self.pos_embed = _RelativePositionEmbedding(context_radius, d_model)
        self.attn = nn.MultiheadAttention(
            d_model, n_heads, dropout=dropout_rate, batch_first=True
        )
        self.out_proj = nn.Linear(d_model, cnn_channels)
        self.dropout = nn.Dropout(dropout_rate)
        self._initialize_weights()

    def _initialize_weights(self) -> None:
        # Only the output projection needs to be zero: q/k/v/attn keep their
        # default init so attention weights are non-degenerate from step 0,
        # but the *delta added back into the CNN feature map* starts at 0.
        nn.init.zeros_(self.out_proj.weight)
        nn.init.zeros_(self.out_proj.bias)

    def forward(self, feat: torch.Tensor, context: torch.Tensor) -> torch.Tensor:
        """Args:
            feat: CNN feature map, ``(B, C, H, W)``.
            context: Context-window embeddings, ``(B, T, embed_dim)``.

        Returns:
            Feature map of the same shape as ``feat``, with the attention
            delta broadcast-added back per column (same value across H).
        """
        B, C, H, W = feat.shape
        avg_w = feat.mean(dim=2)  # (B, C, W)
        max_w = feat.amax(dim=2)  # (B, C, W)
        q_in = torch.cat((avg_w, max_w), dim=1).transpose(1, 2)  # (B, W, 2C)

        q = self.q_proj(q_in)  # (B, W, d_model)
        k = self.k_proj(context) + self.pos_embed(B, feat.device)  # (B, T, d_model)
        v = self.v_proj(context)  # (B, T, d_model)

        attn_out, _ = self.attn(q, k, v, need_weights=False)  # (B, W, d_model)
        delta = self.dropout(self.out_proj(attn_out))  # (B, W, C)
        delta = delta.transpose(1, 2).unsqueeze(2)  # (B, C, 1, W)
        return feat + delta  # broadcasts over H


class CrossAttnDeepSV(nn.Module):
    """DeepSV CNN with cross-attention fusion over a context-window sequence
    of frozen sequence-model embeddings.

    Forward signature matches :class:`~deepsv.models.fused_cnn.FusedDeepSV`:
    ``(image, embedding) → logits`` — but here ``embedding`` must be
    ``(B, T, embed_dim)`` (built by ``FusedDataset(..., context_radius=R)``,
    ``T = 2*R + 1``), not ``(B, embed_dim)``.

    Exposes the same ``cnn_parameters()`` / ``fusion_parameters()`` /
    ``freeze_backbone()`` / ``unfreeze_backbone()`` surface as
    :class:`FusedDeepSV`, so it is a drop-in for
    :class:`~deepsv.training.film_trainer.FiLMTrainer`'s two-stage training
    loop without any trainer changes.
    """

    def __init__(
        self,
        embed_dim: int = 256,
        num_classes: int = 2,
        input_channels: int = 3,
        context_radius: int = 10,
        d_model: int = 128,
        n_heads: int = 4,
        attn_dropout_rate: float = 0.1,
        hooks: Sequence[str] = ("hook3",),
        backbone: Optional[ModernDeletionCNN] = None,
        use_se: bool = True,
        se_reduction: int = 8,
    ) -> None:
        """Args:
        embed_dim: Frozen embedding dimensionality (256 for HyenaDNA-small).
        context_radius: Must match the ``context_radius`` used to build the
            train/val ``FusedDataset`` — how many neighbouring 50 bp windows
            are attended to on each side of the target window.
        hooks: Which CNN hook points to attach cross-attention to. Default
            ``("hook3",)`` — the finer-grained 32-wide spatial map for a
            256x256 input. Pass ``("hook3", "hook4")`` for multi-scale
            attention at both mid-level depths, mirroring FiLM's two-hook
            default at roughly 2x the compute.
        backbone: Optionally inject a pre-existing :class:`ModernDeletionCNN`
            (e.g. warm-started from a trained M0 checkpoint). If ``None``,
            a new one is constructed using ``use_se``/``se_reduction``
            below (ignored if ``backbone`` is given).
        use_se: Only used when ``backbone is None``. See
            :class:`~deepsv.models.cnn.ModernDeletionCNN`.
        se_reduction: Only used when ``backbone is None``.
        """
        super().__init__()
        for h in hooks:
            if h not in _HOOK_CHANNELS:
                raise ValueError(f"Unknown hook {h!r}; must be one of {_VALID_HOOKS}")
        if not hooks:
            raise ValueError("hooks must be non-empty")

        self.embed_dim = embed_dim
        self.context_radius = context_radius
        self.hooks = tuple(hooks)

        self.cnn = (
            backbone
            if backbone is not None
            else ModernDeletionCNN(
                num_classes=num_classes,
                input_channels=input_channels,
                use_se=use_se,
                se_reduction=se_reduction,
            )
        )

        self.attn_blocks = nn.ModuleDict(
            {
                h: WindowCrossAttention(
                    cnn_channels=_HOOK_CHANNELS[h],
                    embed_dim=embed_dim,
                    context_radius=context_radius,
                    d_model=d_model,
                    n_heads=n_heads,
                    dropout_rate=attn_dropout_rate,
                )
                for h in self.hooks
            }
        )

    # ------------------------------------------------------------------
    # Parameter groups for two-stage training (FiLMTrainer-compatible names)
    # ------------------------------------------------------------------

    def cnn_parameters(self):
        """Iterator over backbone parameters (used for the CNN param group)."""
        return self.cnn.parameters()

    def fusion_parameters(self):
        """Iterator over cross-attention parameters (all hooks)."""
        for block in self.attn_blocks.values():
            yield from block.parameters()

    def freeze_backbone(self) -> None:
        """Freeze the CNN backbone (Stage A of two-stage training)."""
        for p in self.cnn.parameters():
            p.requires_grad = False

    def unfreeze_backbone(self) -> None:
        """Unfreeze the CNN backbone (Stage B of two-stage training)."""
        for p in self.cnn.parameters():
            p.requires_grad = True

    # ------------------------------------------------------------------
    # Forward pass
    # ------------------------------------------------------------------

    def forward(self, image: torch.Tensor, embedding: torch.Tensor) -> torch.Tensor:
        """Args:
            image: Tensor of shape ``(B, C, H, W)``.
            embedding: Context-window tensor of shape ``(B, T, embed_dim)``,
                ``T = 2*context_radius + 1``, already cast to the model's
                dtype/device by the dataloader / caller.

        Returns:
            Logits of shape ``(B, num_classes)``.
        """
        if embedding.dim() != 3:
            raise ValueError(
                "CrossAttnDeepSV expects a (B, T, embed_dim) context-window "
                "embedding — build the dataset with context_radius > 0 "
                f"(FusedDataset(..., context_radius={self.context_radius})). "
                f"Got shape {tuple(embedding.shape)}."
            )
        if embedding.shape[1] != 2 * self.context_radius + 1:
            raise ValueError(
                f"embedding has T={embedding.shape[1]} tokens but "
                f"context_radius={self.context_radius} expects "
                f"T={2 * self.context_radius + 1}. Dataset and model "
                "context_radius must match."
            )

        hook_kwargs = {}
        for h in self.hooks:
            block = self.attn_blocks[h]
            hook_kwargs[h] = lambda feat, block=block: block(feat, embedding)

        return self.cnn._forward_features_with_hooks(image, **hook_kwargs)

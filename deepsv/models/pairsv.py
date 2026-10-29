"""Controlled M0--M4 model ladder for the PAIR-SV multisample experiment."""
from __future__ import annotations

from collections.abc import Iterable

import torch
import torch.nn as nn
import torch.nn.functional as F


PAIRSV_VARIANTS = ("M0", "M1", "M2", "M3", "M4")

# Retrained branch-removal ablations for M4 (item 9): each is a genuine
# 2-branch model trained from scratch with that branch structurally absent,
# rather than a post-hoc zero/shuffle intervention on the trained M4. These
# are additive to PAIRSV_VARIANTS -- M0-M4 themselves are unchanged.
M4_ABLATION_VARIANTS = ("M4_NO_CANDIDATE", "M4_NO_READ", "M4_NO_SCALAR")


class BreakpointPileupEncoder(nn.Module):
    """One encoder shared by the left and right ``(6, 64, 128)`` pileups."""

    def __init__(self, output_dim: int = 128, dropout: float = 0.1) -> None:
        super().__init__()
        self.blocks = nn.Sequential(
            self._block(6, 32),
            self._block(32, 64),
            self._block(64, 96),
        )
        self.pool = nn.AdaptiveAvgPool2d((2, 4))
        self.projection = nn.Sequential(
            nn.Flatten(),
            nn.Linear(96 * 2 * 4, output_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )

    @staticmethod
    def _block(input_channels: int, output_channels: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(input_channels, output_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(output_channels),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(output_channels, output_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(output_channels),
            nn.LeakyReLU(0.1, inplace=True),
            nn.MaxPool2d(2),
        )

    def forward(self, pileup: torch.Tensor) -> torch.Tensor:
        if pileup.ndim != 4 or tuple(pileup.shape[1:]) != (6, 64, 128):
            raise ValueError(f"breakpoint pileup must be (B,6,64,128), got {tuple(pileup.shape)}")
        return self.projection(self.pool(self.blocks(pileup)))


class _FeatureBranch(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, dropout: float) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.network = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, output_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        if values.ndim != 2 or values.shape[1] != self.input_dim:
            raise ValueError(f"branch input must be (B,{self.input_dim}), got {tuple(values.shape)}")
        return self.network(values)


class PairSV(nn.Module):
    """PAIR-SV ablation ladder with an explicitly preserved image-only path.

    ``M0`` uses paired pileups only; ``M1`` adds candidate REF/ALT features;
    ``M2`` adds 17 scalar read-support features; ``M3`` adds pooled frozen
    read-sequence embeddings; and ``M4`` uses all branches.

    The single identity-at-initialization mechanism is a zero-initialized final
    projection on the residual fusion head. There is no additional gate, so
    every multimodal variant begins exactly at its own image-only logits.
    """

    BRANCHES_BY_VARIANT = {
        "M0": (),
        "M1": ("candidate",),
        "M2": ("scalar",),
        "M3": ("read",),
        "M4": ("candidate", "read", "scalar"),
        # retrained branch-removal ablations (item 9): each omits exactly one
        # of M4's three branches, trained from scratch -- not a post-hoc
        # zero/shuffle intervention on the already-trained M4.
        "M4_NO_CANDIDATE": ("read", "scalar"),
        "M4_NO_READ": ("candidate", "scalar"),
        "M4_NO_SCALAR": ("candidate", "read"),
    }

    def __init__(
        self,
        variant: str,
        *,
        candidate_dim: int = 1024,
        read_dim: int = 512,
        scalar_dim: int = 17,
        pileup_dim: int = 128,
        branch_dim: int = 128,
        fusion_dim: int = 256,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        variant = variant.upper()
        if variant not in self.BRANCHES_BY_VARIANT:
            raise ValueError(f"variant must be one of {tuple(self.BRANCHES_BY_VARIANT)}, got {variant!r}")
        self.variant = variant
        self.active_branches = self.BRANCHES_BY_VARIANT[variant]
        self.pileup_encoder = BreakpointPileupEncoder(pileup_dim, dropout=dropout / 2)
        self.image_fusion = nn.Sequential(
            nn.Linear(pileup_dim * 4, fusion_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        self.image_classifier = nn.Linear(fusion_dim, 2)

        self.candidate_branch = (
            _FeatureBranch(candidate_dim, branch_dim, dropout)
            if "candidate" in self.active_branches else None
        )
        self.read_branch = (
            _FeatureBranch(read_dim, branch_dim, dropout)
            if "read" in self.active_branches else None
        )
        self.scalar_branch = (
            _FeatureBranch(scalar_dim, branch_dim, dropout)
            if "scalar" in self.active_branches else None
        )
        if self.active_branches:
            self.residual_fusion = nn.Sequential(
                nn.Linear(fusion_dim + branch_dim * len(self.active_branches), fusion_dim),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(fusion_dim, 2),
            )
            nn.init.zeros_(self.residual_fusion[-1].weight)
            nn.init.zeros_(self.residual_fusion[-1].bias)
        else:
            self.residual_fusion = None

    def image_features(self, images: torch.Tensor) -> torch.Tensor:
        if images.ndim != 5 or tuple(images.shape[1:]) != (2, 6, 64, 128):
            raise ValueError(f"paired images must be (B,2,6,64,128), got {tuple(images.shape)}")
        left = self.pileup_encoder(images[:, 0])
        right = self.pileup_encoder(images[:, 1])
        paired = torch.cat((left, right, torch.abs(left - right), left * right), dim=-1)
        return self.image_fusion(paired)

    def forward(
        self,
        images: torch.Tensor,
        *,
        candidate_features: torch.Tensor | None = None,
        read_features: torch.Tensor | None = None,
        scalar_features: torch.Tensor | None = None,
        ablate: Iterable[str] = (),
    ) -> torch.Tensor:
        image_features = self.image_features(images)
        image_logits = self.image_classifier(image_features)
        if not self.active_branches:
            return image_logits

        ablated = set(ablate)
        unknown = ablated - set(self.active_branches)
        if unknown:
            raise ValueError(f"cannot ablate inactive/unknown branches: {sorted(unknown)}")
        inputs = {
            "candidate": (self.candidate_branch, candidate_features),
            "read": (self.read_branch, read_features),
            "scalar": (self.scalar_branch, scalar_features),
        }
        branch_features = []
        for name in self.active_branches:
            branch, values = inputs[name]
            if values is None:
                raise ValueError(f"{self.variant} requires {name}_features")
            encoded = branch(values)
            if name in ablated:
                encoded = torch.zeros_like(encoded)
            branch_features.append(encoded)
        residual = self.residual_fusion(torch.cat((image_features, *branch_features), dim=-1))
        return image_logits + residual


def make_pairsv_model(variant: str, **kwargs) -> PairSV:
    return PairSV(variant, **kwargs)

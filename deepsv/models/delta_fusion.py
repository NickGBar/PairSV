"""Delta-Fusion: candidate-aware REF/ALT late fusion for the second phase.

Single identity-at-init mechanism (per the Stage-2 spec E): the delta head's
final projection is zero-initialised and there is **no gate**, so at step 0

    forward(image, rep) == backbone(image)          (image-only behaviour)

and gradients are usable (the zero-init output layer trains from step 1, then
propagates to the hidden layer). The genomic contribution enters as an additive
logit correction:

    final_logits = image_logits + delta_head(rep)

`rep` is the (already train-normalised) candidate REF/ALT representation
(e.g. abs(E_alt - E_ref)); the backbone is a frozen ModernDeletionCNN.
"""
from __future__ import annotations

import torch
import torch.nn as nn


class DeltaFusion(nn.Module):
    def __init__(self, rep_dim: int, backbone: nn.Module,
                 hidden_dim: int = 128, dropout: float = 0.1) -> None:
        super().__init__()
        self.cnn = backbone  # frozen ModernDeletionCNN -> (B, 2) image logits
        self.head = nn.Sequential(
            nn.Linear(rep_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 2),
        )
        # identity-at-init: zero the FINAL projection only (single mechanism, no gate)
        nn.init.zeros_(self.head[3].weight)
        nn.init.zeros_(self.head[3].bias)

    def forward(self, image: torch.Tensor, rep: torch.Tensor) -> torch.Tensor:
        return self.cnn(image) + self.head(rep)

    def freeze_backbone(self) -> None:
        for p in self.cnn.parameters():
            p.requires_grad_(False)

    def unfreeze_backbone(self) -> None:
        for p in self.cnn.parameters():
            p.requires_grad_(True)

    def fusion_parameters(self):
        return self.head.parameters()

"""PyTorch CNN model for deletion detection"""

from typing import Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F


class SEBlock(nn.Module):
    """Squeeze-and-excitation channel gate.

    Global-average-pools the full ``(H, W)`` feature map to one value per
    channel ("squeeze"), passes it through a small bottleneck MLP
    ("excitation"), and rescales each channel by the resulting sigmoid gate.

    The gate is a single scalar per ``(batch, channel)``, broadcast
    uniformly across every spatial location. That matters here specifically
    because this architecture's classifier head deliberately preserves the
    W axis (genomic position) and only collapses H (the read axis) — see
    ``ModernDeletionCNN._classifier_features``. Multiplying a feature map by
    a per-channel constant cannot alter the *relative* pattern across W
    within a channel, only its overall magnitude, so SE cannot wash out the
    position-preserving signal the rest of the architecture (and the
    cross-attention fusion built on top of it) relies on.

    Reduction ratio defaults to 8 rather than the SE-Net-paper-standard 16:
    at 96 channels (this CNN's width), a 16x reduction leaves only a 6-unit
    bottleneck, which is a tighter squeeze than the 256-2048-channel
    ImageNet backbones the ratio was originally tuned for.
    """

    def __init__(self, channels: int, reduction: int = 8) -> None:
        super().__init__()
        hidden = max(1, channels // reduction)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc1 = nn.Linear(channels, hidden)
        self.fc2 = nn.Linear(hidden, channels)
        # No custom init here: ModernDeletionCNN._initialize_weights() sweeps
        # every nn.Linear (including these) after construction, so whatever
        # this module does at init time would just be overwritten anyway.
        # Deliberately NOT using an identity-at-init trick (unlike FiLM /
        # context calibration / cross-attention): those exist to protect an
        # *already-trained* CNN's behaviour when conditioning heads are
        # added on top. SE is part of the backbone itself, trained from
        # scratch — there's no prior behaviour to protect, and standard
        # SE-Net/EfficientNet init (moderate, ~0.5-ish gates at step 0, not
        # pinned to identity) is the well-evidenced default.

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.shape
        z = self.pool(x).view(b, c)
        z = F.relu(self.fc1(z), inplace=True)
        gate = torch.sigmoid(self.fc2(z)).view(b, c, 1, 1)
        return x * gate


class ModernDeletionCNN(nn.Module):
    """Modern CNN architecture matching the legacy Keras model.

    The forward pass is decomposed into five named blocks so that
    wrapper models can inject FiLM modulation or hooks.
    """

    BLOCK3_CHANNELS: int = 96
    BLOCK4_CHANNELS: int = 96
    CLASSIFIER_X_BINS: int = 16
    CLASSIFIER_FEATURES: int = 256

    def __init__(
        self,
        num_classes: int = 2,
        input_channels: int = 3,
        n_base_filters: int = 96,
        dropout_rate: float = 0.3,
        use_se: bool = True,
        se_reduction: int = 8,
    ):
        """Args (new):
        use_se: Add a squeeze-and-excitation channel gate to each of the 5
            conv blocks (default True — this is the modernized backbone).
            Set False to reproduce the original plain-conv M0 baseline from
            the exact same class, for a fair, same-code comparison.
        se_reduction: SE bottleneck reduction ratio (default 8; see
            :class:`SEBlock`).
        """
        super(ModernDeletionCNN, self).__init__()
        self.use_se = use_se

        # ── Block 1 ──
        self.conv1_1 = nn.Conv2d(
            input_channels, n_base_filters, kernel_size=3, stride=1, padding=1
        )
        self.bn1_1 = nn.BatchNorm2d(n_base_filters)
        self.conv1_2 = nn.Conv2d(
            n_base_filters, n_base_filters, kernel_size=3, stride=1, padding=1
        )
        self.bn1_2 = nn.BatchNorm2d(n_base_filters)
        self.se1 = SEBlock(n_base_filters, se_reduction) if use_se else nn.Identity()
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2, ceil_mode=True)

        # ── Block 2 ──
        self.conv2_1 = nn.Conv2d(
            n_base_filters, n_base_filters, kernel_size=3, stride=1, padding=1
        )
        self.bn2_1 = nn.BatchNorm2d(n_base_filters)
        self.conv2_2 = nn.Conv2d(
            n_base_filters, n_base_filters, kernel_size=3, stride=1, padding=1
        )
        self.bn2_2 = nn.BatchNorm2d(n_base_filters)
        self.se2 = SEBlock(n_base_filters, se_reduction) if use_se else nn.Identity()
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2, ceil_mode=True)

        # ── Block 3 ──
        self.conv3_1 = nn.Conv2d(
            n_base_filters, n_base_filters, kernel_size=3, stride=1, padding=1
        )
        self.bn3_1 = nn.BatchNorm2d(n_base_filters)
        self.conv3_2 = nn.Conv2d(
            n_base_filters, n_base_filters, kernel_size=3, stride=1, padding=1
        )
        self.bn3_2 = nn.BatchNorm2d(n_base_filters)
        self.se3 = SEBlock(n_base_filters, se_reduction) if use_se else nn.Identity()
        self.pool3 = nn.MaxPool2d(kernel_size=2, stride=2, ceil_mode=True)

        # ── Block 4 ──
        self.conv4_1 = nn.Conv2d(
            n_base_filters, n_base_filters, kernel_size=3, stride=1, padding=1
        )
        self.bn4_1 = nn.BatchNorm2d(n_base_filters)
        self.conv4_2 = nn.Conv2d(
            n_base_filters, n_base_filters, kernel_size=3, stride=1, padding=1
        )
        self.bn4_2 = nn.BatchNorm2d(n_base_filters)
        self.se4 = SEBlock(n_base_filters, se_reduction) if use_se else nn.Identity()
        self.pool4 = nn.MaxPool2d(kernel_size=2, stride=2, ceil_mode=True)

        # ── Block 5 ──
        self.conv5 = nn.Conv2d(
            n_base_filters, n_base_filters, kernel_size=3, stride=1, padding=1
        )
        self.bn5 = nn.BatchNorm2d(n_base_filters)
        self.se5 = SEBlock(n_base_filters, se_reduction) if use_se else nn.Identity()
        self.drop5 = nn.Dropout(dropout_rate)

        # ── Classifier ──
        self.flatten = nn.Flatten()
        # Preserve the genomic x-axis while summarising the pileup y-axis.
        # For 255x255 or 256x256 input, 4 pools of 2x2 reduce x to 16 bins.
        # We concatenate y-axis average and max pooling: (B, C, H, W) -> (B, 2C, W).
        self.fc1 = nn.Linear(
            n_base_filters * 2 * self.CLASSIFIER_X_BINS,
            self.CLASSIFIER_FEATURES,
        )
        self.dropout_fc = nn.Dropout(dropout_rate)
        # Note: Added final linear layer for class logits (old Keras code ended with Dropout)
        self.fc2 = nn.Linear(self.CLASSIFIER_FEATURES, num_classes)

        self._initialize_weights()

    def _initialize_weights(self):
        """Initialize model weights"""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(
                    m.weight, mode="fan_out", nonlinearity="leaky_relu"
                )
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)

    def _block1(self, x: torch.Tensor) -> torch.Tensor:
        x = F.leaky_relu(self.bn1_1(self.conv1_1(x)), 0.1, inplace=True)
        x = F.leaky_relu(self.bn1_2(self.conv1_2(x)), 0.1, inplace=True)
        x = self.se1(x)
        x = self.pool1(x)
        return x

    def _block2(self, x: torch.Tensor) -> torch.Tensor:
        x = F.leaky_relu(self.bn2_1(self.conv2_1(x)), 0.1, inplace=True)
        x = F.leaky_relu(self.bn2_2(self.conv2_2(x)), 0.1, inplace=True)
        x = self.se2(x)
        x = self.pool2(x)
        return x

    def _block3(self, x: torch.Tensor) -> torch.Tensor:
        x = F.leaky_relu(self.bn3_1(self.conv3_1(x)), 0.1, inplace=True)
        x = F.leaky_relu(self.bn3_2(self.conv3_2(x)), 0.1, inplace=True)
        x = self.se3(x)
        x = self.pool3(x)
        return x

    def _block4(self, x: torch.Tensor) -> torch.Tensor:
        x = F.leaky_relu(self.bn4_1(self.conv4_1(x)), 0.1, inplace=True)
        x = F.leaky_relu(self.bn4_2(self.conv4_2(x)), 0.1, inplace=True)
        x = self.se4(x)
        x = self.pool4(x)
        return x

    def _block5(self, x: torch.Tensor) -> torch.Tensor:
        x = F.leaky_relu(self.bn5(self.conv5(x)), 0.1, inplace=True)
        x = self.se5(x)
        x = self.drop5(x)
        return x

    def _classifier_features(self, x: torch.Tensor) -> torch.Tensor:
        avg_y = x.mean(dim=2)
        max_y = x.amax(dim=2)
        x = torch.cat((avg_y, max_y), dim=1)
        x = self.flatten(x)
        x = F.relu(self.fc1(x), inplace=True)
        x = self.dropout_fc(x)
        return x

    def _classify_from_features(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(x)

    def _classify(self, x: torch.Tensor) -> torch.Tensor:
        return self._classify_from_features(self._classifier_features(x))

    def _forward_features_with_hooks(
        self,
        x: torch.Tensor,
        hook3=None,
        hook4=None,
        return_classifier_features: bool = False,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        x = self._block1(x)
        x = self._block2(x)

        x = self._block3(x)
        if hook3 is not None:
            x = hook3(x)

        x = self._block4(x)
        if hook4 is not None:
            x = hook4(x)

        x = self._block5(x)
        classifier_features = self._classifier_features(x)
        logits = self._classify_from_features(classifier_features)
        if return_classifier_features:
            return logits, classifier_features
        return logits

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Input tensor of shape (batch_size, channels, height, width)

        Returns:
            Output logits
        """
        return self._forward_features_with_hooks(x)

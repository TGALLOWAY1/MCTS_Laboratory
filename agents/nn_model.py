"""Blokus neural network: ResNet trunk with value and policy heads."""

import torch
import torch.nn as nn
import torch.nn.functional as F

from agents.nn_encoding import NUM_SPATIAL_CHANNELS, NUM_SCALAR_FEATURES


class ResBlock(nn.Module):
    """Residual block: Conv-BN-ReLU-Conv-BN + skip connection."""

    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        return F.relu(out + residual)


class BlokusNet(nn.Module):
    """Small ResNet for Blokus position evaluation and move prediction.

    Architecture:
        Input: 9-channel 20x20 spatial + 85 scalar features
        Trunk: Conv(9->64) + 4 ResBlocks
        Value head: GlobalAvgPool -> MLP -> sigmoid (normalized score)
        Policy head: per-move scoring MLP using spatial features at move cells
    """

    def __init__(self, trunk_channels: int = 64, num_res_blocks: int = 4):
        super().__init__()
        self.trunk_channels = trunk_channels

        # Trunk
        self.input_conv = nn.Conv2d(NUM_SPATIAL_CHANNELS, trunk_channels, 3,
                                     padding=1, bias=False)
        self.input_bn = nn.BatchNorm2d(trunk_channels)
        self.res_blocks = nn.ModuleList(
            [ResBlock(trunk_channels) for _ in range(num_res_blocks)]
        )

        # Value head
        value_input_size = trunk_channels + NUM_SCALAR_FEATURES  # 64 + 85 = 149
        self.value_fc1 = nn.Linear(value_input_size, 64)
        self.value_fc2 = nn.Linear(64, 1)

        # Policy head — scores individual moves
        # Move feature: spatial (trunk_channels) + piece_id (21) + orient (8) + anchor (2) = 95
        move_feature_size = trunk_channels + 21 + 8 + 2
        self.policy_fc1 = nn.Linear(move_feature_size, 64)
        self.policy_fc2 = nn.Linear(64, 1)

    def trunk_forward(self, spatial: torch.Tensor) -> torch.Tensor:
        """Shared trunk: spatial input -> feature maps.

        Args:
            spatial: (B, 9, 20, 20) float tensor

        Returns:
            (B, 64, 20, 20) feature maps
        """
        x = F.relu(self.input_bn(self.input_conv(spatial)))
        for block in self.res_blocks:
            x = block(x)
        return x

    def value_forward(self, features: torch.Tensor,
                      scalar: torch.Tensor) -> torch.Tensor:
        """Value head: predict normalized score for current player.

        Args:
            features: (B, 64, 20, 20) trunk output
            scalar: (B, 85) scalar features

        Returns:
            (B, 1) predicted score in [0, 1]
        """
        pooled = features.mean(dim=(2, 3))  # (B, 64) global average pool
        x = torch.cat([pooled, scalar], dim=1)  # (B, 149)
        x = F.relu(self.value_fc1(x))
        return torch.sigmoid(self.value_fc2(x))

    def policy_score_moves(self, features: torch.Tensor,
                           scalar: torch.Tensor,
                           moves: torch.Tensor,
                           move_masks: torch.Tensor) -> torch.Tensor:
        """Score a batch of candidate moves.

        Args:
            features: (B, 64, 20, 20) trunk output
            scalar: (B, 85) scalar features
            moves: (B, K, 4) int tensor — (piece_id, orientation, anchor_row, anchor_col)
            move_masks: (B, K) bool tensor — True for valid candidates

        Returns:
            (B, K) logits for each move (masked positions get -inf)
        """
        B, K, _ = moves.shape

        # Extract spatial features at each move's anchor position
        anchor_rows = moves[:, :, 2].clamp(0, 19)  # (B, K)
        anchor_cols = moves[:, :, 3].clamp(0, 19)  # (B, K)

        # Gather features at anchor positions: (B, C, H, W) -> (B, K, C)
        # Use grid_sample or manual indexing
        spatial_feats = features[
            torch.arange(B, device=features.device).unsqueeze(1).expand(B, K),
            :,
            anchor_rows,
            anchor_cols
        ]  # (B, K, 64)

        # Encode move metadata
        piece_ids = moves[:, :, 0].clamp(0, 20).long()  # (B, K)
        orientations = moves[:, :, 1].clamp(0, 7).long()  # (B, K)

        piece_onehot = F.one_hot(piece_ids, 21).float()  # (B, K, 21)
        orient_onehot = F.one_hot(orientations, 8).float()  # (B, K, 8)

        # Normalized anchor position
        anchor_norm = torch.stack([
            anchor_rows.float() / 19.0,
            anchor_cols.float() / 19.0
        ], dim=-1)  # (B, K, 2)

        # Concatenate move features
        move_feats = torch.cat([
            spatial_feats, piece_onehot, orient_onehot, anchor_norm
        ], dim=-1)  # (B, K, 95)

        # Score through MLP
        scores = F.relu(self.policy_fc1(move_feats))  # (B, K, 64)
        scores = self.policy_fc2(scores).squeeze(-1)  # (B, K)

        # Mask invalid moves
        scores = scores.masked_fill(~move_masks, float('-inf'))

        return scores

    def forward(self, spatial, scalar):
        """Forward pass returning value prediction only (for simple training)."""
        features = self.trunk_forward(spatial)
        value = self.value_forward(features, scalar)
        return value, features

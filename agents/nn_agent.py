"""Standalone neural network agent for Blokus.

Uses the policy head to score legal moves directly — no tree search.
Instant evaluation via a single CNN forward pass.
"""

import os
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.nn_encoding import encode_board_spatial, encode_board_scalar
from agents.nn_model import BlokusNet
from engine.board import Board, Player
from engine.move_generator import Move


class NNAgent:
    """Neural network agent using policy head for move selection."""

    def __init__(self,
                 model_path: str = "models/blokus_nn_v1.pt",
                 seed: Optional[int] = None,
                 temperature: float = 0.5,
                 device: str = "cpu"):
        self.rng = np.random.RandomState(seed)
        self.temperature = temperature
        self.device = torch.device(device)
        self.model = BlokusNet()

        checkpoint = torch.load(model_path, map_location=self.device,
                                weights_only=True)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def select_action(self, board: Board, player: Player,
                      legal_moves: List[Move]) -> Optional[Move]:
        if not legal_moves:
            return None

        if len(legal_moves) == 1:
            return legal_moves[0]

        # Encode board
        spatial = encode_board_spatial(board.grid, player.value)
        spatial_t = torch.from_numpy(spatial).unsqueeze(0).to(self.device)

        pieces_used = self._encode_pieces_used(board)
        scalar = encode_board_scalar(pieces_used, board.move_count, player.value)
        scalar_t = torch.from_numpy(scalar).unsqueeze(0).to(self.device)

        # Get trunk features
        _, features = self.model(spatial_t, scalar_t)

        # Score all legal moves via policy head
        K = len(legal_moves)
        candidates = torch.zeros(1, K, 4, dtype=torch.long, device=self.device)
        mask = torch.ones(1, K, dtype=torch.bool, device=self.device)

        for i, move in enumerate(legal_moves):
            candidates[0, i] = torch.tensor([
                move.piece_id, move.orientation,
                move.anchor_row, move.anchor_col
            ])

        logits = self.model.policy_score_moves(features, scalar_t,
                                                candidates, mask)  # (1, K)
        logits = logits.squeeze(0)  # (K,)

        # Softmax with temperature
        probs = torch.softmax(logits / self.temperature, dim=0).cpu().numpy()

        # Sample
        idx = self.rng.choice(len(legal_moves), p=probs)
        return legal_moves[idx]

    def _encode_pieces_used(self, board: Board):
        players = list(Player)
        pu = np.zeros((4, 21), dtype=bool)
        for i, p in enumerate(players):
            for pid in board.player_pieces_used[p]:
                pu[i, pid - 1] = True
        return pu

    def get_action_info(self) -> Dict[str, Any]:
        return {
            "name": "NNAgent",
            "type": "nn",
            "description": "Neural network agent (policy head, no search)",
        }

    def reset(self):
        pass

    def set_seed(self, seed: int):
        self.rng = np.random.RandomState(seed)

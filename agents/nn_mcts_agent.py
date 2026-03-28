"""MCTS agent guided by neural network value evaluation.

Replaces FastMCTSAgent's crude heuristic rollout with the NN value head,
which was trained on 337k board states to predict game outcomes.
"""

import os
import sys
from typing import Any, Dict, List, Optional

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.fast_mcts_agent import FastMCTSAgent
from agents.nn_encoding import encode_board_spatial, encode_board_scalar
from agents.nn_model import BlokusNet
from engine.board import Board, Player
from engine.move_generator import Move


class NNMCTSAgent(FastMCTSAgent):
    """FastMCTS with neural network value evaluation replacing random rollouts.

    The NN value head predicts the current player's normalized score from the
    raw board state in a single forward pass (~1ms), replacing the original
    crude heuristic (piece_size + center_distance + noise).
    """

    def __init__(self,
                 model_path: str = "models/blokus_nn_v1.pt",
                 iterations: int = 500,
                 time_limit: float = 0.5,
                 exploration_constant: float = 1.414,
                 seed: Optional[int] = None,
                 device: str = "cpu"):
        super().__init__(
            iterations=iterations,
            time_limit=time_limit,
            exploration_constant=exploration_constant,
            seed=seed,
        )
        self.device = torch.device(device)
        self.model = BlokusNet()
        self._load_model(model_path)
        self.model.eval()

    def _load_model(self, path: str):
        """Load trained model weights."""
        checkpoint = torch.load(path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)

    @torch.no_grad()
    def _fast_rollout(self, board: Board, player: Player) -> float:
        """Replace random rollout with NN value prediction.

        One forward pass through the CNN (~1ms on CPU) instead of
        simulating random moves to game end.
        """
        # Encode board state
        spatial = encode_board_spatial(board.grid, player.value)
        spatial_tensor = torch.from_numpy(spatial).unsqueeze(0).to(self.device)

        # Encode scalar features
        pieces_used = self._encode_pieces_used(board, player)
        scalar = encode_board_scalar(pieces_used, board.move_count, player.value)
        scalar_tensor = torch.from_numpy(scalar).unsqueeze(0).to(self.device)

        # Forward pass — value head only
        value, _ = self.model(spatial_tensor, scalar_tensor)

        return value.item()

    def _encode_pieces_used(self, board: Board, player: Player):
        """Build the 4×21 pieces_used array for encoding."""
        import numpy as np
        players = list(Player)
        pu = np.zeros((4, 21), dtype=bool)
        for i, p in enumerate(players):
            for pid in board.player_pieces_used[p]:
                pu[i, pid - 1] = True
        return pu

    def get_action_info(self) -> Dict[str, Any]:
        return {
            "name": "NNMCTSAgent",
            "type": "nn_mcts",
            "description": "FastMCTS with neural network value evaluation",
        }

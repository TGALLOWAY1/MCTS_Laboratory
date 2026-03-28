"""Encode Blokus board state into tensors for the neural network."""

import numpy as np

from engine.board import Board, Player


# Constants
BOARD_SIZE = 20
NUM_SPATIAL_CHANNELS = 9  # 4 player stones + empty + 4 frontiers
NUM_SCALAR_FEATURES = 85  # 4*21 pieces used + 1 game phase


def encode_board_spatial(board_grid: np.ndarray, current_player: int) -> np.ndarray:
    """Encode board grid into spatial channels.

    Channels (all 20x20 binary planes):
      0: current player's stones
      1-3: opponent stones (in player order, rotated so current is first)
      4: empty cells
      5: current player's frontier
      6-8: opponent frontiers

    Args:
        board_grid: int8 array of shape (20, 20), values 0-4
        current_player: int 1-4

    Returns:
        float32 array of shape (9, 20, 20)
    """
    spatial = np.zeros((NUM_SPATIAL_CHANNELS, BOARD_SIZE, BOARD_SIZE), dtype=np.float32)

    # Player order rotated so current player is always channel 0
    player_order = []
    for i in range(4):
        p = ((current_player - 1 + i) % 4) + 1  # 1-indexed
        player_order.append(p)

    # Channels 0-3: player stones
    for ch, pval in enumerate(player_order):
        spatial[ch] = (board_grid == pval).astype(np.float32)

    # Channel 4: empty
    spatial[4] = (board_grid == 0).astype(np.float32)

    # Channels 5-8: frontiers (requires Board object, approximate from grid)
    # We approximate frontier as: empty cell that is diagonally adjacent to
    # a player's stone but not orthogonally adjacent to same player's stone
    for ch_offset, pval in enumerate(player_order):
        frontier = _compute_frontier_from_grid(board_grid, pval)
        spatial[5 + ch_offset] = frontier

    return spatial


def _compute_frontier_from_grid(grid: np.ndarray, player_val: int) -> np.ndarray:
    """Compute frontier cells for a player from the raw grid.

    Frontier = empty cells diagonally adjacent to player but not
    orthogonally adjacent to same player.
    """
    player_mask = (grid == player_val)
    empty_mask = (grid == 0)
    frontier = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.float32)

    # Diagonal adjacency (corners)
    diag = np.zeros_like(player_mask)
    diag[1:, 1:] |= player_mask[:-1, :-1]
    diag[1:, :-1] |= player_mask[:-1, 1:]
    diag[:-1, 1:] |= player_mask[1:, :-1]
    diag[:-1, :-1] |= player_mask[1:, 1:]

    # Orthogonal adjacency (edges)
    orth = np.zeros_like(player_mask)
    orth[1:, :] |= player_mask[:-1, :]
    orth[:-1, :] |= player_mask[1:, :]
    orth[:, 1:] |= player_mask[:, :-1]
    orth[:, :-1] |= player_mask[:, 1:]

    frontier = (empty_mask & diag & ~orth).astype(np.float32)
    return frontier


def encode_board_scalar(pieces_used: np.ndarray, move_count: int,
                        current_player: int) -> np.ndarray:
    """Encode non-spatial features as a flat vector.

    Args:
        pieces_used: bool array of shape (4, 21)
        move_count: current move count
        current_player: int 1-4

    Returns:
        float32 array of shape (85,)
    """
    # Rotate pieces_used so current player is first
    rotated = np.zeros((4, 21), dtype=np.float32)
    for i in range(4):
        src = ((current_player - 1 + i) % 4)
        rotated[i] = pieces_used[src].astype(np.float32)

    scalar = np.zeros(NUM_SCALAR_FEATURES, dtype=np.float32)
    scalar[:84] = rotated.flatten()
    scalar[84] = min(move_count / 100.0, 1.0)  # game phase

    return scalar

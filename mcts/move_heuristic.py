"""Domain-specific move heuristic for Blokus MCTS action reduction.

Layer 3: Provides fast move scoring for progressive widening ordering
and progressive history bias.

Features
--------
1. **Piece size** — Larger pieces score more and are harder to place later.
2. **Corner generation** — Net new frontier cells created by placement.
3. **Center proximity** — Central territory enables expansion in more directions.
4. **Opponent blocking** — Blocks an opponent's diagonal corner anchor.

The heuristic is normalised to [0, 1] for consistent interaction with the
progressive history weight W.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from engine.board import Board, Player, Position
from engine.move_generator import LegalMoveGenerator, Move, get_shared_generator
from engine.pieces import PieceGenerator

# ---------------------------------------------------------------------------
# Piece size lookup (cached at module level)
# ---------------------------------------------------------------------------

_PIECE_SIZES: Optional[Dict[int, int]] = None


def _get_piece_sizes() -> Dict[int, int]:
    global _PIECE_SIZES
    if _PIECE_SIZES is None:
        pg = PieceGenerator()
        _PIECE_SIZES = {}
        for piece in pg.get_all_pieces():
            _PIECE_SIZES[piece.id] = piece.size
    return _PIECE_SIZES


# ---------------------------------------------------------------------------
# Move-level feature computation (fast)
# ---------------------------------------------------------------------------

def _get_piece_positions(move: Move, move_generator: LegalMoveGenerator) -> List[Position]:
    """Get the board positions a move occupies."""
    orientations = move_generator.piece_orientations_cache[move.piece_id]
    orientation = orientations[move.orientation]
    positions = []
    rows, cols = orientation.shape
    for i in range(rows):
        for j in range(cols):
            if orientation[i, j] == 1:
                positions.append(Position(move.anchor_row + i, move.anchor_col + j))
    return positions


def compute_move_heuristic(
    board: Board,
    player: Player,
    move: Move,
    move_generator: LegalMoveGenerator,
    *,
    w_piece_size: float = 1.0,
    w_corners: float = 2.0,
    w_center: float = 0.5,
    w_blocking: float = 1.0,
) -> float:
    """Score a single move using domain-specific Blokus features.

    Returns a raw (un-normalised) heuristic score.  Higher is better.
    """
    sizes = _get_piece_sizes()
    piece_size = sizes.get(move.piece_id, 3)

    # --- piece size ---
    h_size = piece_size / 5.0  # normalise to ~[0.2, 1.0]

    # --- corner generation ---
    positions = _get_piece_positions(move, move_generator)
    new_corners = 0
    occupied_set = set((p.row, p.col) for p in positions)
    for pos in positions:
        for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            nr, nc = pos.row + dr, pos.col + dc
            if 0 <= nr < board.SIZE and 0 <= nc < board.SIZE:
                if board.grid[nr, nc] == 0 and (nr, nc) not in occupied_set:
                    # Check no orthogonal adjacency to player's existing pieces
                    # or the new placement itself
                    blocked = False
                    for er, ec in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        enr, enc = nr + er, nc + ec
                        if 0 <= enr < board.SIZE and 0 <= enc < board.SIZE:
                            if board.grid[enr, enc] == player.value:
                                blocked = True
                                break
                            if (enr, enc) in occupied_set:
                                blocked = True
                                break
                    if not blocked:
                        new_corners += 1
    h_corners = min(new_corners / 8.0, 1.0)  # normalise (8 corners = excellent)

    # --- center proximity ---
    centroid_row = sum(p.row for p in positions) / len(positions)
    centroid_col = sum(p.col for p in positions) / len(positions)
    max_dist = 9.5 * np.sqrt(2)
    dist = np.sqrt((centroid_row - 9.5) ** 2 + (centroid_col - 9.5) ** 2)
    h_center = 1.0 - (dist / max_dist)

    # --- opponent blocking ---
    h_blocking = 0.0
    for pos in positions:
        for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            nr, nc = pos.row + dr, pos.col + dc
            if 0 <= nr < board.SIZE and 0 <= nc < board.SIZE:
                cell = board.grid[nr, nc]
                if cell != 0 and cell != player.value:
                    # This move is diagonally adjacent to an opponent piece —
                    # it may block their frontier.
                    h_blocking += 0.25  # Each adjacency contributes a bit
    h_blocking = min(h_blocking, 1.0)

    raw = (
        w_piece_size * h_size
        + w_corners * h_corners
        + w_center * h_center
        + w_blocking * h_blocking
    )
    return raw


def compute_move_heuristic_normalised(
    board: Board,
    player: Player,
    move: Move,
    move_generator: LegalMoveGenerator,
    **kwargs,
) -> float:
    """Score a move and normalise to [0, 1]."""
    raw = compute_move_heuristic(board, player, move, move_generator, **kwargs)
    # Theoretical max ≈ 1.0 + 2.0 + 0.5 + 1.0 = 4.5
    return min(max(raw / 4.5, 0.0), 1.0)


# ---------------------------------------------------------------------------
# Batch scoring for move ordering
# ---------------------------------------------------------------------------

def rank_moves_by_heuristic(
    board: Board,
    player: Player,
    moves: List[Move],
    move_generator: LegalMoveGenerator,
    **kwargs,
) -> List[Tuple[float, Move]]:
    """Score all moves and return sorted list (ascending — best move last for pop()).

    Returns list of (score, move) tuples sorted by score ascending.
    """
    scored = [
        (compute_move_heuristic(board, player, m, move_generator, **kwargs), m)
        for m in moves
    ]
    scored.sort(key=lambda x: x[0])  # ascending: worst first, best last
    return scored


# ---------------------------------------------------------------------------
# Progressive history action key
# ---------------------------------------------------------------------------

def move_action_key(move: Move) -> int:
    """Abstract action key for progressive history.

    Uses ``piece_id`` as the abstraction — this generalises across board
    positions and orientations, capturing "which piece is good to play now?"
    knowledge that transfers across different board states.
    """
    return move.piece_id

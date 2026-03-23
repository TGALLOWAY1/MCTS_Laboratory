"""Lightweight state evaluation function for Blokus MCTS simulation strategy.

Layer 4: Provides fast board-state evaluation for:
- Early rollout termination (4.2) — cut off rollouts and evaluate statically
- Two-ply search-based playouts (4.1) — score resulting states after candidate moves

Features
--------
1. **squares_placed** — Squares occupied by the player (score proxy).
2. **remaining_piece_area** — Total area of unused pieces (lower is better).
3. **accessible_corners** — Frontier cells (placement anchors) available.
4. **reachable_empty_squares** — Empty cells near frontier (expansion potential).
5. **largest_remaining_piece_size** — Largest piece still available.
6. **opponent_avg_mobility** — Average opponent frontier size (negative weight).
7. **territory_enclosure_area** — Placeholder (weight=0, too expensive for per-step eval).

Output is normalised to [0, 1] for compatibility with Q-values.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from engine.board import Board, Player

# ---------------------------------------------------------------------------
# Piece size lookup (reuse pattern from mcts/move_heuristic.py)
# ---------------------------------------------------------------------------

_PIECE_SIZES: Optional[Dict[int, int]] = None
_TOTAL_PIECE_AREA: int = 0


def _get_piece_sizes() -> Dict[int, int]:
    global _PIECE_SIZES, _TOTAL_PIECE_AREA
    if _PIECE_SIZES is None:
        from engine.pieces import PieceGenerator
        pg = PieceGenerator()
        _PIECE_SIZES = {}
        for piece in pg.get_all_pieces():
            _PIECE_SIZES[piece.id] = piece.size
        _TOTAL_PIECE_AREA = sum(_PIECE_SIZES.values())  # 89 squares
    return _PIECE_SIZES


# Pre-compute player list to avoid repeated allocations
_PLAYERS = list(Player)

# ---------------------------------------------------------------------------
# Default weights — tuned to produce a balanced [0, 1] score
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: Dict[str, float] = {
    "squares_placed": 0.30,
    "remaining_piece_area": -0.15,
    "accessible_corners": 0.25,
    "reachable_empty_squares": 0.10,
    "largest_remaining_piece_size": 0.10,
    "opponent_avg_mobility": -0.10,
    "territory_enclosure_area": 0.00,  # placeholder — too expensive for per-step eval
}

# Normalization constants
_MAX_FRONTIER = 40.0  # reasonable upper bound for frontier cells
_MAX_REACHABLE = 60.0  # bounded BFS limit


class BlokusStateEvaluator:
    """Fast board-state evaluation for Blokus MCTS rollout strategies.

    Designed to be called at every step of every simulation — all features
    use pre-computed data on the Board object to stay under 0.5ms/call.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = dict(weights) if weights else dict(DEFAULT_WEIGHTS)
        self._piece_sizes = _get_piece_sizes()
        self._total_piece_area = _TOTAL_PIECE_AREA

    def evaluate(self, board: Board, player: Player) -> float:
        """Evaluate a board state for *player*.  Returns a value in [0, 1]."""
        w = self.weights
        pieces_used = board.player_pieces_used[player]

        # 1. squares_placed  — normalised by total piece area (89)
        squares = float(np.sum(board.grid == player.value))
        f_squares = squares / max(self._total_piece_area, 1)

        # 2. remaining_piece_area  — fraction of area still unplaced
        remaining = sum(
            sz for pid, sz in self._piece_sizes.items() if pid not in pieces_used
        )
        f_remaining = remaining / max(self._total_piece_area, 1)

        # 3. accessible_corners  — frontier size
        frontier = board.get_frontier(player)
        f_corners = min(len(frontier) / _MAX_FRONTIER, 1.0)

        # 4. reachable_empty_squares — bounded BFS from frontier
        f_reachable = self._reachable_empty(board, frontier)

        # 5. largest_remaining_piece_size
        largest = 0
        for pid, sz in self._piece_sizes.items():
            if pid not in pieces_used and sz > largest:
                largest = sz
        f_largest = largest / 5.0  # max piece size is 5

        # 6. opponent_avg_mobility — average frontier across opponents
        opp_frontier_sum = 0
        opp_count = 0
        for p in _PLAYERS:
            if p != player:
                opp_frontier_sum += len(board.get_frontier(p))
                opp_count += 1
        f_opp_mobility = min(
            (opp_frontier_sum / max(opp_count, 1)) / _MAX_FRONTIER, 1.0
        )

        # 7. territory_enclosure_area — placeholder (weight=0)
        f_territory = 0.0

        # Weighted sum
        raw = (
            w["squares_placed"] * f_squares
            + w["remaining_piece_area"] * f_remaining
            + w["accessible_corners"] * f_corners
            + w["reachable_empty_squares"] * f_reachable
            + w["largest_remaining_piece_size"] * f_largest
            + w["opponent_avg_mobility"] * f_opp_mobility
            + w["territory_enclosure_area"] * f_territory
        )

        # Clamp to [0, 1]
        return max(0.0, min(1.0, raw))

    @staticmethod
    def _reachable_empty(
        board: Board,
        frontier: set,
        max_cells: int = 60,
    ) -> float:
        """Bounded BFS from frontier cells counting reachable empty squares.

        Explores orthogonally-adjacent empty cells starting from each frontier
        cell, up to *max_cells* total.  Returns normalised count.
        """
        if not frontier:
            return 0.0

        grid = board.grid
        size = board.SIZE
        visited = set()
        queue = list(frontier)  # frontier cells are already empty by definition
        count = 0

        # BFS over empty neighbours of frontier
        head = 0
        while head < len(queue) and count < max_cells:
            r, c = queue[head]
            head += 1
            if (r, c) in visited:
                continue
            visited.add((r, c))
            # Only count cells outside the frontier itself
            if (r, c) not in frontier:
                count += 1
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size:
                    if grid[nr, nc] == 0 and (nr, nc) not in visited:
                        queue.append((nr, nc))

        return min(count / _MAX_REACHABLE, 1.0)

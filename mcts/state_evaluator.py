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
    "squares_placed": 0.03,
    "remaining_piece_area": -0.03,
    "accessible_corners": 0.24,
    "reachable_empty_squares": 0.08,
    "largest_remaining_piece_size": -0.23,
    "opponent_avg_mobility": -0.10,
    "center_proximity": 0.25,
    "territory_enclosure_area": 0.00,  # placeholder — too expensive for per-step eval
}

# Normalization constants
_MAX_FRONTIER = 40.0  # reasonable upper bound for frontier cells
_MAX_REACHABLE = 60.0  # bounded BFS limit
_CENTER = 9.5  # board center coordinate (20x20 grid, indices 0-19)
_MAX_CENTER_DIST = 19.0  # max Manhattan distance from center: |0-9.5|+|0-9.5|


FEATURE_NAMES = [
    "squares_placed",
    "remaining_piece_area",
    "accessible_corners",
    "reachable_empty_squares",
    "largest_remaining_piece_size",
    "opponent_avg_mobility",
    "center_proximity",
    "territory_enclosure_area",
]

# Phase-occupancy thresholds (calibrated from Layer 1 branching factor curve)
PHASE_EARLY_THRESHOLD = 0.25
PHASE_LATE_THRESHOLD = 0.55


class BlokusStateEvaluator:
    """Fast board-state evaluation for Blokus MCTS rollout strategies.

    Designed to be called at every step of every simulation — all features
    use pre-computed data on the Board object to stay under 0.5ms/call.

    Supports optional phase-dependent weight vectors (Layer 6).  When
    *phase_weights* is provided, the evaluator selects the weight vector
    matching the current game phase (early / mid / late) based on board
    occupancy.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        phase_weights: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        self.weights = dict(weights) if weights else dict(DEFAULT_WEIGHTS)
        self.phase_weights = phase_weights  # {"early": {...}, "mid": {...}, "late": {...}}
        self._piece_sizes = _get_piece_sizes()
        self._total_piece_area = _TOTAL_PIECE_AREA

    # ------------------------------------------------------------------
    # Phase detection
    # ------------------------------------------------------------------

    @staticmethod
    def get_phase(board: Board) -> str:
        """Determine game phase from board occupancy.

        Returns ``"early"``, ``"mid"``, or ``"late"``.
        """
        occupancy = float(np.count_nonzero(board.grid)) / (board.SIZE * board.SIZE)
        if occupancy < PHASE_EARLY_THRESHOLD:
            return "early"
        elif occupancy < PHASE_LATE_THRESHOLD:
            return "mid"
        return "late"

    # ------------------------------------------------------------------
    # Feature extraction (raw normalised values)
    # ------------------------------------------------------------------

    def extract_features(self, board: Board, player: Player) -> Dict[str, float]:
        """Return the raw normalised feature dict for *player*.

        This is the same computation used by :meth:`evaluate` but returns
        the individual feature values instead of the weighted sum.
        """
        pieces_used = board.player_pieces_used[player]

        player_mask = board.grid == player.value
        squares = float(np.sum(player_mask))
        f_squares = squares / max(self._total_piece_area, 1)

        remaining = sum(
            sz for pid, sz in self._piece_sizes.items() if pid not in pieces_used
        )
        f_remaining = remaining / max(self._total_piece_area, 1)

        frontier = board.get_frontier(player)
        f_corners = min(len(frontier) / _MAX_FRONTIER, 1.0)

        f_reachable = self._reachable_empty(board, frontier)

        largest = 0
        for pid, sz in self._piece_sizes.items():
            if pid not in pieces_used and sz > largest:
                largest = sz
        f_largest = largest / 5.0

        opp_frontier_sum = 0
        opp_count = 0
        for p in _PLAYERS:
            if p != player:
                opp_frontier_sum += len(board.get_frontier(p))
                opp_count += 1
        f_opp_mobility = min(
            (opp_frontier_sum / max(opp_count, 1)) / _MAX_FRONTIER, 1.0
        )

        # center_proximity: 1 = pieces clustered at center, 0 = at edges
        if squares > 0:
            coords = np.argwhere(player_mask)
            mean_dist = float(
                np.mean(np.abs(coords[:, 0] - _CENTER) + np.abs(coords[:, 1] - _CENTER))
            )
            f_center = 1.0 - mean_dist / _MAX_CENTER_DIST
        else:
            f_center = 0.0

        f_territory = 0.0

        return {
            "squares_placed": f_squares,
            "remaining_piece_area": f_remaining,
            "accessible_corners": f_corners,
            "reachable_empty_squares": f_reachable,
            "largest_remaining_piece_size": f_largest,
            "opponent_avg_mobility": f_opp_mobility,
            "center_proximity": f_center,
            "territory_enclosure_area": f_territory,
        }

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        board: Board,
        player: Player,
        weight_adjustments: Optional[Dict[str, float]] = None,
    ) -> float:
        """Evaluate a board state for *player*.  Returns a value in [0, 1].

        Args:
            board: Current board state.
            player: Player to evaluate for.
            weight_adjustments: Optional dict of weight deltas (from Layer 7
                opponent modeling) to add to the base weight vector.
        """
        features = self.extract_features(board, player)

        # Select weight vector: phase-dependent if available, else global
        if self.phase_weights:
            phase = self.get_phase(board)
            w = self.phase_weights[phase]
        else:
            w = self.weights

        # Apply Layer 7 defensive weight adjustments if provided
        if weight_adjustments:
            w = {k: w.get(k, 0.0) + weight_adjustments.get(k, 0.0) for k in
                 set(w) | set(weight_adjustments)}

        raw = sum(w.get(k, 0.0) * v for k, v in features.items())

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

"""
Enhanced heuristic agent for Blokus with 10 strategic features.

Extends the original HeuristicAgent's 4 features with 6 additional features
covering opponent awareness, frontier management, spatial reasoning, and
piece economy. Designed for weight optimization via genetic algorithm.
"""

from typing import Any, Dict, List, Optional

import numpy as np

from engine.board import Board, Player, Position
from engine.move_generator import LegalMoveGenerator, Move, get_shared_generator
from engine.pieces import PieceGenerator


# Orientation counts per piece (1-indexed, piece IDs 1-21)
# Used for piece versatility feature
_ORIENTATION_COUNTS = {
    1: 1, 2: 2, 3: 2, 4: 4, 5: 2, 6: 1, 7: 4, 8: 8, 9: 4, 10: 4,
    11: 8, 12: 2, 13: 8, 14: 8, 15: 8, 16: 4, 17: 4, 18: 4, 19: 4,
    20: 1, 21: 8,
}
_MAX_ORIENTATIONS = 8  # for normalization


class EnhancedHeuristicAgent:
    """
    Enhanced heuristic agent with 10 weighted features:

    Original 4:
      1. piece_size         — prefer larger pieces
      2. corner_creation    — maximize new corner opportunities
      3. edge_avoidance     — penalize board-edge placement
      4. center_preference  — prefer central positions

    New 6:
      5. opponent_blocking      — occupy opponents' frontier cells
      6. corners_killed         — own frontier cells lost by this move
      7. opponent_proximity     — distance to nearest opponent pieces
      8. open_space             — local freedom around placed piece
      9. piece_versatility      — preserve flexible pieces for endgame
     10. blocking_risk          — vulnerability of new corners to opponents
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.RandomState(seed)
        self.move_generator = get_shared_generator()
        self.piece_generator = PieceGenerator()

        # Original 4 weights (same defaults as HeuristicAgent)
        self.piece_size_weight = 1.0
        self.corner_creation_weight = 2.0
        self.edge_avoidance_weight = -1.5
        self.center_preference_weight = 0.5

        # New 6 weights
        self.opponent_blocking_weight = 1.5
        self.corners_killed_weight = -1.0
        self.opponent_proximity_weight = -0.5
        self.open_space_weight = 0.5
        self.piece_versatility_weight = -0.3
        self.blocking_risk_weight = -0.5

    def select_action(self, board: Board, player: Player,
                      legal_moves: List[Move]) -> Optional[Move]:
        if not legal_moves:
            return None

        move_scores = []
        for move in legal_moves:
            score = self._evaluate_move(board, player, move)
            move_scores.append(score)

        scores_array = np.array(move_scores)
        probabilities = self._softmax(scores_array, temperature=1.0)
        move_idx = self.rng.choice(len(legal_moves), p=probabilities)
        return legal_moves[move_idx]

    def _evaluate_move(self, board: Board, player: Player, move: Move) -> float:
        score = 0.0

        piece = self.piece_generator.get_piece_by_id(move.piece_id)
        orientations = self.move_generator.piece_orientations_cache[move.piece_id]
        orientation = orientations[move.orientation]
        piece_positions = self._get_piece_positions(move, orientation)

        # ── Original 4 features ──

        # 1. Piece size
        score += self.piece_size_weight * piece.size

        # 2. Corner creation
        corner_score = self._evaluate_corner_creation(board, player, piece_positions)
        score += self.corner_creation_weight * corner_score

        # 3. Edge avoidance
        edge_score = self._evaluate_edge_avoidance(board, piece_positions)
        score += self.edge_avoidance_weight * edge_score

        # 4. Center preference
        center_score = self._evaluate_center_preference(move)
        score += self.center_preference_weight * center_score

        # ── New 6 features ──

        # 5. Opponent blocking — how many opponent frontier cells do we occupy?
        blocking_score = self._evaluate_opponent_blocking(board, player, piece_positions)
        score += self.opponent_blocking_weight * blocking_score

        # 6. Corners killed — how many of our OWN frontier cells does this move destroy?
        killed_score = self._evaluate_corners_killed(board, player, piece_positions)
        score += self.corners_killed_weight * killed_score

        # 7. Opponent proximity — average min distance to opponent pieces
        proximity_score = self._evaluate_opponent_proximity(board, player, piece_positions)
        score += self.opponent_proximity_weight * proximity_score

        # 8. Open space — local freedom around placed piece
        space_score = self._evaluate_open_space(board, piece_positions)
        score += self.open_space_weight * space_score

        # 9. Piece versatility preservation — penalize using flexible pieces early
        versatility_score = self._evaluate_piece_versatility(board, move.piece_id)
        score += self.piece_versatility_weight * versatility_score

        # 10. Blocking risk — are our new corners vulnerable to opponents?
        risk_score = self._evaluate_blocking_risk(board, player, piece_positions)
        score += self.blocking_risk_weight * risk_score

        return score

    # ── Original features (reimplemented to match HeuristicAgent) ──

    def _evaluate_corner_creation(self, board: Board, player: Player,
                                  piece_positions: List[Position]) -> float:
        piece_pos_set = {(p.row, p.col) for p in piece_positions}
        new_corners = 0
        for pos in piece_positions:
            for adj_pos in board.get_corner_adjacent_positions(pos):
                if not board.is_empty(adj_pos):
                    continue
                if (adj_pos.row, adj_pos.col) in piece_pos_set:
                    continue
                safe = True
                for edge_pos in board.get_edge_adjacent_positions(adj_pos):
                    if (edge_pos.row, edge_pos.col) in piece_pos_set:
                        safe = False
                        break
                    if board.get_player_at(edge_pos) == player:
                        safe = False
                        break
                if safe:
                    new_corners += 1
        return float(new_corners)

    def _evaluate_edge_avoidance(self, board: Board,
                                 piece_positions: List[Position]) -> float:
        edge_positions = 0
        for pos in piece_positions:
            min_distance = min(pos.row, pos.col,
                               Board.SIZE - 1 - pos.row,
                               Board.SIZE - 1 - pos.col)
            if min_distance <= 2:
                edge_positions += 1
        game_progress = board.move_count / 100.0
        if game_progress < 0.3:
            return float(edge_positions)
        return float(edge_positions) * 0.5

    def _evaluate_center_preference(self, move: Move) -> float:
        center = 9.5
        dist = np.sqrt((move.anchor_row - center) ** 2 +
                        (move.anchor_col - center) ** 2)
        max_dist = np.sqrt(2 * (center ** 2))
        return 1.0 - dist / max_dist

    # ── New features ──

    def _evaluate_opponent_blocking(self, board: Board, player: Player,
                                    piece_positions: List[Position]) -> float:
        """Count opponent frontier cells that our piece occupies.

        Each such cell is a placement anchor the opponent permanently loses.
        """
        piece_coords = {(p.row, p.col) for p in piece_positions}
        blocked = 0
        for opp in Player:
            if opp == player:
                continue
            opp_frontier = board.get_frontier(opp)
            for coord in piece_coords:
                if coord in opp_frontier:
                    blocked += 1
        return float(blocked)

    def _evaluate_corners_killed(self, board: Board, player: Player,
                                 piece_positions: List[Position]) -> float:
        """Count our own frontier cells that become invalid after this move.

        A frontier cell is killed if it becomes occupied by our piece or
        becomes edge-adjacent to our piece (violating the Blokus placement
        rule for same-color pieces).
        """
        piece_coords = {(p.row, p.col) for p in piece_positions}
        our_frontier = board.get_frontier(player)
        killed = 0
        for fr, fc in our_frontier:
            # Killed if occupied by our piece
            if (fr, fc) in piece_coords:
                killed += 1
                continue
            # Killed if edge-adjacent to any of our placed squares
            for pos in piece_positions:
                if abs(fr - pos.row) + abs(fc - pos.col) == 1:
                    killed += 1
                    break
        return float(killed)

    def _evaluate_opponent_proximity(self, board: Board, player: Player,
                                     piece_positions: List[Position]) -> float:
        """Average minimum Chebyshev distance from each placed square to
        the nearest opponent square.

        Lower values = closer to opponents (aggressive positioning).
        Uses a sampled scan for efficiency on the 20x20 board.
        """
        # Collect opponent positions (sample grid at stride 2 for speed)
        opp_positions = []
        for r in range(0, Board.SIZE, 2):
            for c in range(0, Board.SIZE, 2):
                cell = board.get_cell(Position(r, c))
                if cell != 0 and cell != player.value:
                    opp_positions.append((r, c))

        if not opp_positions:
            return 0.0

        total_dist = 0.0
        for pos in piece_positions:
            min_d = min(max(abs(pos.row - or_), abs(pos.col - oc))
                        for or_, oc in opp_positions)
            total_dist += min_d

        return total_dist / len(piece_positions)

    def _evaluate_open_space(self, board: Board,
                             piece_positions: List[Position]) -> float:
        """Count unique empty cells within Manhattan distance 2 of placed squares.

        Measures local breathing room — more open space means more future
        placement flexibility in this region.
        """
        piece_coords = {(p.row, p.col) for p in piece_positions}
        seen = set()
        empty_count = 0
        for pos in piece_positions:
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    if abs(dr) + abs(dc) > 2:
                        continue
                    r, c = pos.row + dr, pos.col + dc
                    if (r, c) in seen or (r, c) in piece_coords:
                        continue
                    seen.add((r, c))
                    if 0 <= r < Board.SIZE and 0 <= c < Board.SIZE:
                        if board.is_empty(Position(r, c)):
                            empty_count += 1
        return float(empty_count)

    def _evaluate_piece_versatility(self, board: Board, piece_id: int) -> float:
        """Penalize using high-versatility pieces early in the game.

        Pieces with many orientations (like pentomino L with 8) are more
        flexible and thus more valuable to save for the endgame when space
        is tight. The penalty decays as the game progresses.
        """
        orientations = _ORIENTATION_COUNTS.get(piece_id, 1)
        normalized = orientations / _MAX_ORIENTATIONS  # 0..1

        game_progress = board.move_count / 100.0
        # High versatility early = high penalty; late game = no penalty
        return normalized * max(0.0, 1.0 - game_progress)

    def _evaluate_blocking_risk(self, board: Board, player: Player,
                                piece_positions: List[Position]) -> float:
        """Count new corners we create that are edge-adjacent to opponent pieces.

        These corners are "at risk" — an opponent can easily place a piece
        that occupies or blocks them, making our expansion fragile.
        """
        piece_coords = {(p.row, p.col) for p in piece_positions}
        at_risk = 0

        for pos in piece_positions:
            for adj_pos in board.get_corner_adjacent_positions(pos):
                if not board.is_empty(adj_pos):
                    continue
                if (adj_pos.row, adj_pos.col) in piece_coords:
                    continue
                # Is this a valid new corner for us?
                safe_for_us = True
                for edge_pos in board.get_edge_adjacent_positions(adj_pos):
                    if (edge_pos.row, edge_pos.col) in piece_coords:
                        safe_for_us = False
                        break
                    if board.get_player_at(edge_pos) == player:
                        safe_for_us = False
                        break
                if not safe_for_us:
                    continue

                # Check if any opponent piece is edge-adjacent to this corner
                for edge_pos in board.get_edge_adjacent_positions(adj_pos):
                    opp = board.get_player_at(edge_pos)
                    if opp is not None and opp != player:
                        at_risk += 1
                        break

        return float(at_risk)

    # ── Utility ──

    def _get_piece_positions(self, move: Move,
                             orientation: np.ndarray) -> List[Position]:
        positions = []
        rows, cols = orientation.shape
        for i in range(rows):
            for j in range(cols):
                if orientation[i, j] == 1:
                    positions.append(Position(move.anchor_row + i,
                                              move.anchor_col + j))
        return positions

    def _softmax(self, x: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        x_scaled = x / temperature
        x_shifted = x_scaled - np.max(x_scaled)
        exp_x = np.exp(x_shifted)
        return exp_x / np.sum(exp_x)

    def get_action_info(self) -> Dict[str, Any]:
        return {
            "name": "EnhancedHeuristicAgent",
            "type": "enhanced_heuristic",
            "description": "10-feature strategic agent with opponent awareness",
            "weights": {
                "piece_size": self.piece_size_weight,
                "corner_creation": self.corner_creation_weight,
                "edge_avoidance": self.edge_avoidance_weight,
                "center_preference": self.center_preference_weight,
                "opponent_blocking": self.opponent_blocking_weight,
                "corners_killed": self.corners_killed_weight,
                "opponent_proximity": self.opponent_proximity_weight,
                "open_space": self.open_space_weight,
                "piece_versatility": self.piece_versatility_weight,
                "blocking_risk": self.blocking_risk_weight,
            }
        }

    def reset(self):
        pass

    def set_seed(self, seed: int):
        self.rng = np.random.RandomState(seed)

    def set_weights(self, weights: Dict[str, float]):
        for name, value in weights.items():
            attr = f"{name}_weight"
            if hasattr(self, attr):
                setattr(self, attr, value)

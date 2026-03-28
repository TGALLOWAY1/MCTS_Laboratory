
import os
import time
from typing import Any, Dict, Optional

from analytics.metrics import (
    MetricInput,
    compute_blocking_metrics,
    compute_center_metrics,
    compute_corner_metrics,
    compute_mobility_metrics,
    compute_piece_metrics,
    compute_proximity_metrics,
    compute_territory_metrics,
)
from engine.board import Board, Player
from engine.move_generator import LegalMoveGenerator, Move
from engine.pieces import PieceGenerator

from .schemas import GameResultLog, MCTSStepDiagnostics, StepLog


# Cache piece sizes (piece_id -> number of squares)
_PIECE_SIZE_CACHE: Dict[int, int] = {}


def _get_piece_size(piece_id: int) -> int:
    """Look up piece size (number of squares) by piece_id, with caching."""
    if piece_id not in _PIECE_SIZE_CACHE:
        piece = PieceGenerator.get_piece_by_id(piece_id)
        _PIECE_SIZE_CACHE[piece_id] = piece.size if piece else 0
    return _PIECE_SIZE_CACHE[piece_id]


class StrategyLogger:
    def __init__(self, log_dir: str = "logs/analytics"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        self.steps_path = os.path.join(log_dir, "steps.jsonl")
        self.results_path = os.path.join(log_dir, "results.jsonl")

        # Cache for move expansion
        self.move_generator = LegalMoveGenerator()

        # Running score totals per player (reset on_reset)
        self._running_scores: Dict[int, int] = {}

    def log_step(self, item: StepLog):
        with open(self.steps_path, "a") as f:
            f.write(item.model_dump_json() + "\n")

    def log_result(self, item: GameResultLog):
        with open(self.results_path, "a") as f:
            f.write(item.model_dump_json() + "\n")

    def on_reset(self, game_id: str, seed: int, agent_ids: Dict[int, str], config: Dict[str, Any]):
        self.current_game_id = game_id
        self.current_seed = seed
        self.agent_map = agent_ids
        # Reset running scores for the new game
        self._running_scores = {p.value: 0 for p in Player}

    def on_step(
        self,
        game_id: str,
        turn_index: int,
        player_id: int,
        state: Board,
        move: Move,
        next_state: Board,
        mcts_stats: Optional[Dict[str, Any]] = None,
        decision_time_ms: Optional[float] = None,
    ):
        # 1. Expand move to placed squares
        orientations = self.move_generator.piece_orientations_cache.get(move.piece_id)
        if not orientations:
            logging_orientations = PieceGenerator.generate_orientations_for_piece(
                move.piece_id, PieceGenerator.get_piece_by_id(move.piece_id).shape
            )
            placed_squares = move.get_positions(logging_orientations)
        else:
            placed_squares = move.get_positions(orientations)

        placed_tuples = [(p.row, p.col) for p in placed_squares]

        # 2. Identify opponents
        opponents = [p.value for p in Player if p.value != player_id]

        # 3. Construct MetricInput
        inp = MetricInput(
            state=state,
            move=move,
            next_state=next_state,
            player_id=player_id,
            opponents=opponents,
            placed_squares=placed_tuples,
            precomputed_values={},
        )

        # 4. Compute metrics
        from analytics.metrics.mobility import get_mobility_counts

        counts_before, counts_after = get_mobility_counts(inp)
        inp.precomputed_values["mobility_counts_before"] = counts_before
        inp.precomputed_values["mobility_counts_after"] = counts_after

        metrics = {}
        metrics.update(compute_center_metrics(inp))
        metrics.update(compute_territory_metrics(inp))
        metrics.update(compute_mobility_metrics(inp))
        metrics.update(compute_blocking_metrics(inp))
        metrics.update(compute_corner_metrics(inp))
        metrics.update(compute_proximity_metrics(inp))
        metrics.update(compute_piece_metrics(inp))

        # 5. Action details
        action_dict = {
            "piece_id": move.piece_id,
            "orientation": move.orientation,
            "anchor_row": move.anchor_row,
            "anchor_col": move.anchor_col,
        }

        # Basic counts
        legal_moves_before = counts_before.get(player_id, 0)
        legal_moves_after = counts_after.get(player_id, 0)

        # Pieces remaining
        pieces_used = next_state.player_pieces_used.get(Player(player_id), set())
        remaining = [i for i in range(1, 22) if i not in pieces_used]

        # 6. Per-player score deltas and running totals
        score_deltas: Dict[str, int] = {}
        running_scores: Dict[str, int] = {}
        for p in Player:
            pid = p.value
            score_before = state.get_score(p)
            score_after = next_state.get_score(p)
            delta = score_after - score_before
            score_deltas[str(pid)] = delta
            self._running_scores[pid] = self._running_scores.get(pid, 0) + delta
            running_scores[str(pid)] = self._running_scores[pid]

        # 7. MCTS diagnostics (if MCTS stats provided)
        mcts_diag = None
        if mcts_stats:
            piece_size = _get_piece_size(move.piece_id)
            mcts_diag = MCTSStepDiagnostics(
                decision_time_ms=decision_time_ms or mcts_stats.get("time_elapsed", 0.0) * 1000.0,
                iterations=mcts_stats.get("iterations_run"),
                branching_factor=mcts_stats.get("root_legal_moves") or mcts_stats.get("branching_factor"),
                tree_depth_max=mcts_stats.get("tree_depth_max"),
                tree_depth_mean=mcts_stats.get("tree_depth_mean"),
                tree_size=mcts_stats.get("tree_size"),
                visit_entropy=mcts_stats.get("visit_entropy"),
                best_move_q=mcts_stats.get("best_move_q"),
                best_move_visits=mcts_stats.get("best_move_visits"),
                second_best_q=mcts_stats.get("second_best_q"),
                regret_gap=mcts_stats.get("regret_gap"),
                piece_id=move.piece_id,
                piece_size=piece_size,
                piece_anchor_row=move.anchor_row,
                piece_anchor_col=move.anchor_col,
            )

        # 8. Build log entry
        log_entry = StepLog(
            game_id=game_id,
            timestamp=time.time(),
            seed=getattr(self, "current_seed", None),
            turn_index=turn_index,
            player_id=player_id,
            action=action_dict,
            legal_moves_before=legal_moves_before,
            legal_moves_after=legal_moves_after,
            pieces_remaining=remaining,
            metrics=metrics,
            mcts_diagnostics=mcts_diag,
            score_deltas=score_deltas,
            running_scores=running_scores,
            round_index=turn_index // 4,
            position_in_round=turn_index % 4,
            seat_index=player_id - 1,
        )

        self.log_step(log_entry)

    def on_game_end(self, game_id: str, final_scores: Dict[int, int], winner_id: Optional[int], num_turns: int):
        scores_str = {str(k): v for k, v in final_scores.items()}
        seat_order = [p.value for p in Player]
        agent_map_str = {str(k): v for k, v in getattr(self, "agent_map", {}).items()}

        log_entry = GameResultLog(
            game_id=game_id,
            timestamp=time.time(),
            final_scores=scores_str,
            winner_id=winner_id,
            num_turns=num_turns,
            agent_ids=agent_map_str,
            seat_order=seat_order,
        )

        self.log_result(log_entry)

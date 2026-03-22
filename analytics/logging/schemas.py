
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MCTSStepDiagnostics(BaseModel):
    """MCTS-specific diagnostics captured per move decision."""

    decision_time_ms: Optional[float] = None
    iterations: Optional[int] = None
    branching_factor: Optional[int] = None
    tree_depth_max: Optional[int] = None
    tree_depth_mean: Optional[float] = None
    tree_size: Optional[int] = None
    visit_entropy: Optional[float] = None
    best_move_q: Optional[float] = None
    best_move_visits: Optional[int] = None
    second_best_q: Optional[float] = None
    regret_gap: Optional[float] = None
    piece_id: Optional[int] = None
    piece_size: Optional[int] = None
    piece_anchor_row: Optional[int] = None
    piece_anchor_col: Optional[int] = None


class StepLog(BaseModel):
    """Schema for per-step move log."""

    game_id: str
    timestamp: float
    seed: Optional[int]
    turn_index: int
    player_id: int

    # Action details
    action: Dict[str, Any]

    # Board state (optional/minimal)
    board_hash: Optional[str] = None

    # Basic counts
    pieces_remaining: Optional[List[int]] = None  # List of pieces remaining for this player
    legal_moves_before: int
    legal_moves_after: int

    # Derived metrics
    metrics: Dict[str, Any]

    # MCTS diagnostics (only populated when agent is MCTS-based)
    mcts_diagnostics: Optional[MCTSStepDiagnostics] = None

    # Per-player score deltas and running totals
    score_deltas: Optional[Dict[str, int]] = None
    running_scores: Optional[Dict[str, int]] = None

    # Round alignment (additive/optional)
    round_index: Optional[int] = None
    position_in_round: Optional[int] = None
    seat_index: Optional[int] = None


class GameResultLog(BaseModel):
    """Schema for game end result."""

    game_id: str
    timestamp: float
    final_scores: Dict[str, int]  # Keyed by player_id (str to be safe for JSON)
    winner_id: Optional[int]
    num_turns: int
    agent_ids: Dict[str, str]  # map player_id -> agent_name/id
    seat_order: List[int]

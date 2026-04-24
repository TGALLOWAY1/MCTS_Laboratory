"""
Search trace data structures for MCTS visualization.

Collects per-iteration metrics during MCTS search to enable
time-series visualizations of search behavior: depth, breadth,
exploration vs exploitation, rollout outcomes, and UCT breakdowns.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class IterationRecord:
    """Metrics captured at a single MCTS iteration checkpoint."""
    iteration: int
    selected_depth: int = 0         # depth of selected path this iteration
    expanded_depth: int = 0         # depth where expansion occurred
    max_tree_depth: int = 0         # current max depth in entire tree
    tree_size: int = 0              # total nodes in tree
    root_children_count: int = 0    # number of expanded root children
    avg_branching: float = 0.0      # avg children per expanded node
    exploitation_term: float = 0.0  # avg exploitation along selected path
    exploration_term: float = 0.0   # avg exploration along selected path
    best_move_changed: bool = False # did best root child change vs previous?


@dataclass
class RootChildSnapshot:
    """Snapshot of a root child's statistics at a checkpoint."""
    action_id: str          # "piece_id:ori@r,c"
    piece_id: int
    orientation: int
    anchor_row: int
    anchor_col: int
    visits: int
    q_value: float
    probability: float      # normalized visit probability


@dataclass
class RootSnapshotCheckpoint:
    """Root children stats at a particular iteration checkpoint."""
    iteration: int
    children: List[RootChildSnapshot] = field(default_factory=list)


@dataclass
class UctChildBreakdown:
    """UCT term breakdown for a single root child."""
    action_id: str
    piece_id: int
    orientation: int
    anchor_row: int
    anchor_col: int
    visits: int
    parent_visits: int
    exploitation: float     # Q/N (blended)
    exploration: float      # C * sqrt(ln(N_parent)/N)
    rave_q: float = 0.0     # RAVE Q-value (if enabled)
    rave_beta: float = 0.0  # RAVE blending weight
    total: float = 0.0      # total UCT score


@dataclass
class SearchTrace:
    """Aggregated trace data from a single MCTS search.

    Collected during the search loop and attached to the agent for
    retrieval via get_search_trace(). Designed for efficient sampling:
    iteration_records are captured every ``sample_rate`` iterations,
    while rollout_results stores all raw outcomes.
    """
    # Per-iteration time-series (sampled)
    iteration_records: List[IterationRecord] = field(default_factory=list)

    # Raw rollout outcome values (all iterations)
    rollout_results: List[float] = field(default_factory=list)

    # Root children snapshots at percentage checkpoints
    root_snapshots: List[RootSnapshotCheckpoint] = field(default_factory=list)

    # UCT breakdown for root children at end of search
    uct_breakdown: List[UctChildBreakdown] = field(default_factory=list)

    # Board cells explored (row, col) — accumulated across all expanded moves
    explored_cells: List[Tuple[int, int]] = field(default_factory=list)

    # 20x20 exploration count grid (how many times each cell was in an expanded move)
    exploration_grid: Optional[List[List[int]]] = None

    # Configuration
    sample_rate: int = 10
    total_iterations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "depthOverTime": [
                {
                    "iter": r.iteration,
                    "maxDepth": r.max_tree_depth,
                    "avgDepth": r.selected_depth,
                    "selectedDepth": r.selected_depth,
                }
                for r in self.iteration_records
            ],
            "breadthOverTime": [
                {
                    "iter": r.iteration,
                    "treeSize": r.tree_size,
                    "rootChildren": r.root_children_count,
                    "avgBranching": round(r.avg_branching, 2),
                }
                for r in self.iteration_records
            ],
            "explorationOverTime": [
                {
                    "iter": r.iteration,
                    "avgExploitation": round(r.exploitation_term, 4),
                    "avgExploration": round(r.exploration_term, 4),
                    "ratio": (
                        round(r.exploration_term / r.exploitation_term, 4)
                        if r.exploitation_term > 0 else 0.0
                    ),
                }
                for r in self.iteration_records
            ],
            "rolloutResults": self.rollout_results,
            "rootChildrenSnapshots": [
                {
                    "checkpoint": snap.iteration,
                    "children": [
                        {
                            "actionId": c.action_id,
                            "pieceId": c.piece_id,
                            "orientation": c.orientation,
                            "anchorRow": c.anchor_row,
                            "anchorCol": c.anchor_col,
                            "visits": c.visits,
                            "qValue": round(c.q_value, 4),
                            "prob": round(c.probability, 4),
                        }
                        for c in snap.children
                    ],
                }
                for snap in self.root_snapshots
            ],
            "uctBreakdown": [
                {
                    "actionId": u.action_id,
                    "pieceId": u.piece_id,
                    "orientation": u.orientation,
                    "anchorRow": u.anchor_row,
                    "anchorCol": u.anchor_col,
                    "visits": u.visits,
                    "parentVisits": u.parent_visits,
                    "exploitation": round(u.exploitation, 4),
                    "exploration": round(u.exploration, 4),
                    "raveQ": round(u.rave_q, 4),
                    "raveBeta": round(u.rave_beta, 4),
                    "total": round(u.total, 4),
                }
                for u in self.uct_breakdown
            ],
            "explorationGrid": self.exploration_grid,
            "totalIterations": self.total_iterations,
            "sampleRate": self.sample_rate,
        }

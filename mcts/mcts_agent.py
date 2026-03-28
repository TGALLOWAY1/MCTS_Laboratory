"""
Monte Carlo Tree Search agent for Blokus.

Layer 3 additions: Progressive Widening and Progressive History for
action reduction in high-branching-factor games.

Layer 4 additions: Simulation Strategy — two-ply search-based playouts,
early rollout termination with state evaluation, and implicit minimax
backups for multi-player robustness.

Layer 5 additions: RAVE (Rapid Action Value Estimation) for cold-start
bootstrapping — per-node action statistics from rollout moves blend with
UCT Q-values via configurable equivalence constant k. NST (N-gram
Selection Technique) biases rollout move selection using 2-gram
same-player move pair statistics.

Layer 7 additions: Opponent Modeling — asymmetric rollout policies
(different move selection for self vs opponents), blocking-rate tracking,
alliance detection, king-maker awareness, and adaptive opponent profiles
for repeated play.

Layer 8 additions: Parallelization — root parallelization (independent
trees merged at decision time via multiprocessing) and tree parallelization
with virtual loss (shared tree via threading). Root parallelization is the
default and recommended strategy for Python due to the GIL.

Layer 9 additions: Meta-Optimization — adaptive exploration constant that
scales with branching factor, adaptive rollout depth inversely proportional
to branching factor, UCT sufficiency threshold (auto-calibrating α) that
switches to pure exploitation when a dominant move emerges, and loss
avoidance that redirects selection away from catastrophic nodes.
"""

import math
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from agents.heuristic_agent import HeuristicAgent
from engine.board import Board, Player, Position, _PLAYERS
from engine.move_generator import LegalMoveGenerator, Move, get_shared_generator
from engine.pieces import PieceGenerator

from .learned_evaluator import LearnedWinProbabilityEvaluator
from .move_heuristic import (
    compute_move_heuristic,
    move_action_key,
    rank_moves_by_heuristic,
)
from .opponent_model import OpponentModelManager
from .search_trace import (
    IterationRecord,
    RootChildSnapshot,
    RootSnapshotCheckpoint,
    SearchTrace,
    UctChildBreakdown,
)
from .state_evaluator import BlokusStateEvaluator
from .utils import compute_policy_entropy
from .zobrist import TranspositionTable, ZobristHash


class MCTSNode:
    """
    Node in the Monte Carlo Tree Search tree.
    """

    def __init__(
        self,
        board: Board,
        player: Player,
        move: Optional[Move] = None,
        parent: Optional['MCTSNode'] = None,
        heuristic_sorted: bool = False,
    ):
        """
        Initialize MCTS node.

        Args:
            board: Board state at this node
            player: Player whose turn it is
            move: Move that led to this node
            parent: Parent node
            heuristic_sorted: If True, untried_moves are already heuristic-sorted
        """
        self.board = board.copy()
        self.player = player
        self.move = move
        self.parent = parent
        self.children: List[MCTSNode] = []

        # MCTS statistics
        self.visits = 0
        self.total_reward = 0.0
        self.prior_bias = 0.0
        self.untried_moves: List[Move] = []
        self._heuristic_sorted = heuristic_sorted
        # Track the total legal move count (before any widening)
        self._total_legal_moves = 0

        # Layer 4: Implicit minimax backup value
        self.minimax_value: float = float('-inf')

        # Layer 5: RAVE (Rapid Action Value Estimation) per-node statistics
        # Keyed by action_key (piece_id). Updated during backprop for all
        # moves seen in the rollout below this node.
        self.rave_total: Dict[int, float] = {}
        self.rave_visits: Dict[int, int] = {}

        # Layer 9: Loss avoidance flag — set when a catastrophic result is
        # back-propagated through this node, causing selection to prefer siblings.
        self.loss_detected = False

        # Layer 8: Virtual loss for tree parallelization.
        # Temporarily penalizes a node's UCB score while a thread is simulating
        # below it, discouraging other threads from the same path.
        self.virtual_losses: int = 0

        # Initialize untried moves
        self._initialize_untried_moves()

    def _initialize_untried_moves(self):
        """Initialize list of untried moves.

        If the current player has no legal moves (must pass), we check whether
        ANY player can still move. If so, this is a pass node — not terminal.
        We store a sentinel ``[None]`` so that ``expand()`` creates a single
        pass child that advances to the next player with the same board state.
        If no player can move, the node is truly terminal (empty list).
        """
        move_generator = get_shared_generator()
        self.untried_moves = move_generator.get_legal_moves(self.board, self.player)
        self._total_legal_moves = len(self.untried_moves)
        self._is_pass_node = False

        if not self.untried_moves:
            # Check if any other player can still move
            for p in _PLAYERS:
                if p != self.player and move_generator.has_legal_moves(self.board, p):
                    # This is a pass — sentinel so expand() creates a pass child
                    self.untried_moves = [None]
                    self._is_pass_node = True
                    break

    def is_fully_expanded(self) -> bool:
        """Check if node is fully expanded (all legal moves tried)."""
        return len(self.untried_moves) == 0

    def is_terminal(self) -> bool:
        """Check if node is terminal (no player can move)."""
        return len(self.untried_moves) == 0 and len(self.children) == 0

    def max_children_for_visits(self, pw_c: float, pw_alpha: float) -> int:
        """Progressive widening child limit: C_pw * N^alpha."""
        if self.visits <= 0:
            return max(1, int(pw_c))
        return max(1, int(pw_c * (self.visits ** pw_alpha)))

    def should_expand_pw(self, pw_c: float, pw_alpha: float) -> bool:
        """Whether progressive widening allows another child expansion."""
        if not self.untried_moves:
            return False
        return len(self.children) < self.max_children_for_visits(pw_c, pw_alpha)

    def blended_q(self, alpha: float = 0.0) -> float:
        """Return Q-value blended with implicit minimax backup.

        Q_hat = (1 - alpha) * (r/n) + alpha * v_minimax

        When alpha is 0.0 this is identical to standard averaging.
        """
        if self.visits == 0:
            return 0.0
        avg_q = self.total_reward / self.visits
        if alpha <= 0.0 or self.minimax_value == float('-inf'):
            return avg_q
        return (1.0 - alpha) * avg_q + alpha * self.minimax_value

    def apply_virtual_loss(self, magnitude: float = 1.0) -> None:
        """Apply virtual loss during tree-parallel selection.

        Temporarily inflates visit count and decreases reward, discouraging
        other threads from selecting this node.
        """
        self.virtual_losses += 1
        self.visits += 1
        self.total_reward -= magnitude

    def remove_virtual_loss(self, magnitude: float = 1.0) -> None:
        """Remove virtual loss after backpropagation completes."""
        self.virtual_losses = max(0, self.virtual_losses - 1)
        self.visits = max(0, self.visits - 1)
        self.total_reward += magnitude

    def ucb1_value(
        self,
        exploration_constant: float = 1.414,
        progressive_bias_weight: float = 0.0,
        progressive_history_weight: float = 0.0,
        history_score: float = 0.0,
        minimax_alpha: float = 0.0,
        rave_q: float = 0.0,
        rave_beta: float = 0.0,
    ) -> float:
        """
        Calculate UCB1 value with optional progressive bias, progressive history, and RAVE.

        Q_combined = (1 - beta) * Q_UCT + beta * Q_RAVE
        UCB = Q_combined + C*sqrt(ln(N_parent)/N) + W_bias*(prior_bias/(1+N)) + W_hist*(H(a)/(1+N))

        where Q_UCT = Q_hat (blended averaging + minimax), and beta is the RAVE
        weighting factor that decays with parent visits.

        Layer 8: When virtual losses are active, the visit count and total
        reward already include the virtual loss penalty (applied in-place by
        apply_virtual_loss), so the standard formulas naturally produce a
        lower UCB score for nodes being explored by other threads.

        Args:
            exploration_constant: Exploration parameter (sqrt(2) is common)
            progressive_bias_weight: Weight for learned-model bias (Layer 2)
            progressive_history_weight: Weight for progressive history bias (Layer 3)
            history_score: H(a) — historical win rate of this move's action key
            minimax_alpha: Blending weight for implicit minimax backup (Layer 4)
            rave_q: Q_RAVE(s, a) — RAVE value for this child's action (Layer 5)
            rave_beta: RAVE blending weight beta (Layer 5)

        Returns:
            UCB1 value
        """
        if self.visits == 0:
            return float('inf')

        exploitation = self.blended_q(minimax_alpha)

        # Layer 5: Blend UCT Q-value with RAVE Q-value
        if rave_beta > 0.0:
            exploitation = (1.0 - rave_beta) * exploitation + rave_beta * rave_q

        exploration = exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)

        bias_term = progressive_bias_weight * (self.prior_bias / (1.0 + self.visits))
        history_term = progressive_history_weight * (history_score / (1.0 + self.visits))
        return exploitation + exploration + bias_term + history_term

    def select_child(
        self,
        exploration_constant: float = 1.414,
        progressive_bias_weight: float = 0.0,
        progressive_history_weight: float = 0.0,
        history_table: Optional[Dict] = None,
        minimax_alpha: float = 0.0,
        rave_enabled: bool = False,
        rave_k: float = 1000.0,
        loss_avoidance: bool = False,
    ) -> 'MCTSNode':
        """
        Select child node using UCB1 + progressive history + minimax + RAVE.

        Args:
            exploration_constant: Exploration parameter
            progressive_bias_weight: Weight for learned-model bias
            progressive_history_weight: Weight for progressive history
            history_table: {action_key: (total_reward, count)} table
            minimax_alpha: Blending weight for implicit minimax backup (Layer 4)
            rave_enabled: Whether to use RAVE blending (Layer 5)
            rave_k: RAVE equivalence constant (Layer 5)
            loss_avoidance: Avoid children flagged with loss_detected (Layer 9)

        Returns:
            Selected child node
        """
        # Layer 5: Pre-compute RAVE beta from parent visits
        r_beta = 0.0
        if rave_enabled and self.visits > 0:
            r_beta = math.sqrt(rave_k / (3.0 * self.visits + rave_k))

        def _ucb(child: 'MCTSNode') -> float:
            h_score = 0.0
            if progressive_history_weight > 0 and history_table and child.move is not None:
                key = move_action_key(child.move)
                entry = history_table.get(key)
                if entry is not None:
                    total, count = entry
                    h_score = total / count if count > 0 else 0.0

            # Layer 5: Compute RAVE Q-value from parent's RAVE table
            child_rave_q = 0.0
            child_rave_beta = 0.0
            if r_beta > 0.0 and child.move is not None:
                akey = move_action_key(child.move)
                rv = self.rave_visits.get(akey, 0)
                if rv > 0:
                    child_rave_q = self.rave_total[akey] / rv
                    child_rave_beta = r_beta

            return child.ucb1_value(
                exploration_constant=exploration_constant,
                progressive_bias_weight=progressive_bias_weight,
                progressive_history_weight=progressive_history_weight,
                history_score=h_score,
                minimax_alpha=minimax_alpha,
                rave_q=child_rave_q,
                rave_beta=child_rave_beta,
            )

        # Layer 9: Loss avoidance — prefer children not flagged as catastrophic
        if loss_avoidance:
            safe = [c for c in self.children if not c.loss_detected]
            if safe:
                chosen = max(safe, key=_ucb)
            else:
                # All flagged — clear flags and fall through to normal selection
                for c in self.children:
                    c.loss_detected = False
                chosen = max(self.children, key=_ucb)
            # One-shot: clear the flag after redirecting
            chosen.loss_detected = False
            return chosen

        return max(self.children, key=_ucb)

    def expand(self) -> 'MCTSNode':
        """
        Expand node by adding a new child.

        If this is a pass node (current player has no legal moves but other
        players do), creates a single child with the same board state and
        the next player to move.

        Returns:
            New child node
        """
        if not self.untried_moves:
            return None

        # Select random untried move
        move = self.untried_moves.pop()

        # Handle pass node — same board, advance to next player
        if move is None:
            next_player = self._get_next_player()
            child = MCTSNode(self.board, next_player, None, self)
            self.children.append(child)
            return child

        # Create new board state
        new_board = self.board.copy()
        success = new_board.place_piece(
            self._get_move_positions(move),
            self.player,
            move.piece_id,
            validate=False
        )

        if not success:
            return None

        # Determine next player
        next_player = self._get_next_player()

        # Create child node
        child = MCTSNode(new_board, next_player, move, self)
        self.children.append(child)

        return child

    def _get_move_positions(self, move: Move) -> List[Position]:
        """Get positions that a move would occupy."""
        move_generator = get_shared_generator()
        orientations = move_generator.piece_orientations_cache[move.piece_id]
        orientation = orientations[move.orientation]

        positions = []
        rows, cols = orientation.shape

        for i in range(rows):
            for j in range(cols):
                if orientation[i, j] == 1:
                    pos = Position(move.anchor_row + i, move.anchor_col + j)
                    positions.append(pos)

        return positions

    def _get_next_player(self) -> Player:
        """Get next player in turn order."""
        current_idx = _PLAYERS.index(self.player)
        next_idx = (current_idx + 1) % len(_PLAYERS)
        return _PLAYERS[next_idx]

    def update(self, reward: float):
        """
        Update node statistics.
        
        Args:
            reward: Reward from simulation
        """
        self.visits += 1
        self.total_reward += reward

    def get_best_move(self) -> Optional[Move]:
        """
        Get the best move based on visit counts.
        
        Returns:
            Best move or None if no children
        """
        if not self.children:
            return None

        best_child = max(self.children, key=lambda child: child.visits)
        return best_child.move


class MCTSAgent:
    """
    Monte Carlo Tree Search agent for Blokus.
    
    Uses UCT (Upper Confidence Bound applied to Trees) algorithm with
    heuristic rollouts and Zobrist hashing for efficient state representation.
    """

    def __init__(
        self,
        iterations: int = 1000,
        time_limit: Optional[float] = None,
        exploration_constant: float = 1.414,
        rollout_agent: Optional[HeuristicAgent] = None,
        use_transposition_table: bool = True,
        seed: Optional[int] = None,
        learned_model_path: Optional[str] = None,
        leaf_evaluation_enabled: bool = False,
        progressive_bias_enabled: bool = False,
        progressive_bias_weight: float = 0.25,
        potential_shaping_enabled: bool = False,
        potential_shaping_gamma: float = 1.0,
        potential_shaping_weight: float = 1.0,
        potential_mode: str = "prob",
        max_rollout_moves: int = 50,
        # --- Layer 3: Action Reduction ---
        progressive_widening_enabled: bool = False,
        pw_c: float = 2.0,
        pw_alpha: float = 0.5,
        progressive_history_enabled: bool = False,
        progressive_history_weight: float = 1.0,
        heuristic_move_ordering: bool = False,
        # --- Layer 4: Simulation Strategy ---
        rollout_policy: str = "heuristic",
        two_ply_top_k: Optional[int] = None,
        rollout_cutoff_depth: Optional[int] = None,
        state_eval_weights: Optional[Dict[str, float]] = None,
        state_eval_phase_weights: Optional[Dict[str, Dict[str, float]]] = None,
        minimax_backup_alpha: float = 0.0,
        # --- Layer 5: History Heuristics & RAVE ---
        rave_enabled: bool = False,
        rave_k: float = 1000.0,
        nst_enabled: bool = False,
        nst_weight: float = 0.5,
        # --- Layer 7: Opponent Modeling ---
        opponent_rollout_policy: str = "same",
        opponent_modeling_enabled: bool = False,
        alliance_detection_enabled: bool = False,
        alliance_threshold: float = 2.0,
        kingmaker_detection_enabled: bool = False,
        kingmaker_score_gap: int = 15,
        adaptive_opponent_enabled: bool = False,
        defensive_weight_shift: float = 0.15,
        # --- Layer 8: Parallelization ---
        num_workers: int = 1,
        virtual_loss: float = 1.0,
        parallel_strategy: str = "root",
        # --- Layer 9: Meta-Optimization ---
        adaptive_exploration_enabled: bool = False,
        adaptive_exploration_base: float = 1.414,
        adaptive_exploration_avg_bf: float = 80.0,
        adaptive_rollout_depth_enabled: bool = False,
        adaptive_rollout_depth_base: int = 20,
        adaptive_rollout_depth_avg_bf: float = 80.0,
        sufficiency_threshold_enabled: bool = False,
        loss_avoidance_enabled: bool = False,
        loss_avoidance_threshold: float = -50.0,
        # --- Search Trace (Visualization) ---
        enable_search_trace: bool = False,
        search_trace_sample_rate: int = 10,
    ):
        """
        Initialize MCTS agent.

        Args:
            iterations: Maximum number of MCTS iterations
            time_limit: Maximum time in seconds (overrides iterations)
            exploration_constant: UCB1 exploration parameter
            rollout_agent: Agent to use for rollouts (default: HeuristicAgent)
            use_transposition_table: Whether to use transposition table
            seed: Random seed for reproducible behavior
            learned_model_path: Optional model artifact path (`.pkl`) for learned evaluation
            leaf_evaluation_enabled: Enable learned leaf evaluation in place of rollout
            progressive_bias_enabled: Enable progressive bias term from learned value deltas
            progressive_bias_weight: Selection bias weight (decays with child visits)
            potential_shaping_enabled: Enable potential-based shaping in truncated rollouts
            potential_shaping_gamma: Gamma term in shaping: gamma * Phi(s') - Phi(s)
            potential_shaping_weight: Scale factor for shaping contribution
            potential_mode: Potential representation ('prob' or 'logit')
            max_rollout_moves: Maximum rollout length when rollouts are used
            progressive_widening_enabled: Enable progressive widening (Layer 3)
            pw_c: Progressive widening coefficient (children at visit=1)
            pw_alpha: Progressive widening exponent (growth rate)
            progressive_history_enabled: Enable progressive history bias in UCB (Layer 3)
            progressive_history_weight: Weight W for history term in UCB formula
            heuristic_move_ordering: Sort untried moves by domain heuristic (Layer 3)
            rollout_policy: Rollout move selection — "heuristic", "random", or "two_ply" (Layer 4)
            two_ply_top_k: Top-K filter for two-ply rollouts (None = all moves) (Layer 4)
            rollout_cutoff_depth: Cut off rollout at this depth and eval statically (None = full) (Layer 4)
            state_eval_weights: Custom weights for BlokusStateEvaluator (Layer 4)
            state_eval_phase_weights: Phase-dependent weight dicts {"early": {...}, "mid": {...}, "late": {...}} (Layer 6)
            minimax_backup_alpha: Blending weight for implicit minimax backups (0.0 = off) (Layer 4)
            rave_enabled: Enable RAVE (Rapid Action Value Estimation) blending (Layer 5)
            rave_k: RAVE equivalence constant; beta = sqrt(k / (3*N + k)) (Layer 5)
            nst_enabled: Enable N-gram Selection Technique for rollout bias (Layer 5)
            nst_weight: Bias weight for NST-scored moves during rollout (Layer 5)
            opponent_rollout_policy: Rollout policy for opponents — "same" (use self policy),
                "random", or "heuristic" (Layer 7)
            opponent_modeling_enabled: Master switch for opponent tracking (Layer 7)
            alliance_detection_enabled: Detect opponents targeting root player (Layer 7)
            alliance_threshold: Blocking rate multiplier to flag targeting (default 2.0) (Layer 7)
            kingmaker_detection_enabled: Detect late-game king-maker scenarios (Layer 7)
            kingmaker_score_gap: Score gap threshold for king-maker classification (Layer 7)
            adaptive_opponent_enabled: Build cross-game opponent profiles (Layer 7)
            defensive_weight_shift: Eval weight shift magnitude when under threat (Layer 7)
            num_workers: Number of parallel MCTS workers (1 = single-threaded) (Layer 8)
            virtual_loss: Virtual loss magnitude for tree parallelization (Layer 8)
            parallel_strategy: "root" (independent trees, merge) or "tree" (shared tree,
                virtual loss + threading) (Layer 8)
            adaptive_exploration_enabled: Enable branching-factor-adaptive C (Layer 9)
            adaptive_exploration_base: Base exploration constant for adaptive C (Layer 9)
            adaptive_exploration_avg_bf: Average branching factor for C normalisation (Layer 9)
            adaptive_rollout_depth_enabled: Enable branching-factor-adaptive rollout depth (Layer 9)
            adaptive_rollout_depth_base: Base rollout cutoff depth for adaptive depth (Layer 9)
            adaptive_rollout_depth_avg_bf: Average branching factor for depth normalisation (Layer 9)
            sufficiency_threshold_enabled: Enable UCT sufficiency threshold (Layer 9)
            loss_avoidance_enabled: Enable loss avoidance — redirect away from catastrophic
                nodes during selection (Layer 9)
            loss_avoidance_threshold: Reward threshold below which a result is catastrophic (Layer 9)
        """
        self.iterations = iterations
        self.time_limit = time_limit
        self.exploration_constant = exploration_constant
        self.use_transposition_table = use_transposition_table
        self.leaf_evaluation_enabled = bool(leaf_evaluation_enabled)
        self.progressive_bias_enabled = bool(progressive_bias_enabled)
        self.progressive_bias_weight = float(progressive_bias_weight)
        self.potential_shaping_enabled = bool(potential_shaping_enabled)
        self.potential_shaping_gamma = float(potential_shaping_gamma)
        self.potential_shaping_weight = float(potential_shaping_weight)
        self.potential_mode = potential_mode
        self.learned_model_path = learned_model_path
        self.max_rollout_moves = int(max_rollout_moves)

        # Layer 3 params
        self.progressive_widening_enabled = bool(progressive_widening_enabled)
        self.pw_c = float(pw_c)
        self.pw_alpha = float(pw_alpha)
        self.progressive_history_enabled = bool(progressive_history_enabled)
        self.progressive_history_weight = float(progressive_history_weight)
        self.heuristic_move_ordering = bool(heuristic_move_ordering)

        # Layer 4 params
        if rollout_policy not in {"heuristic", "random", "two_ply"}:
            raise ValueError(
                f"rollout_policy must be 'heuristic', 'random', or 'two_ply', got '{rollout_policy}'"
            )
        self.rollout_policy = rollout_policy
        self.two_ply_top_k = int(two_ply_top_k) if two_ply_top_k is not None else None
        self.rollout_cutoff_depth = (
            int(rollout_cutoff_depth) if rollout_cutoff_depth is not None else None
        )
        self.minimax_backup_alpha = float(minimax_backup_alpha)
        self._eval_reward_scale = 100.0  # match win-bonus magnitude

        # Layer 5 params
        self.rave_enabled = bool(rave_enabled)
        self.rave_k = float(rave_k)
        self.nst_enabled = bool(nst_enabled)
        self.nst_weight = float(nst_weight)

        # Layer 7 params
        if opponent_rollout_policy not in {"same", "random", "heuristic"}:
            raise ValueError(
                f"opponent_rollout_policy must be 'same', 'random', or 'heuristic', "
                f"got '{opponent_rollout_policy}'"
            )
        self.opponent_rollout_policy = opponent_rollout_policy
        self.opponent_modeling_enabled = bool(opponent_modeling_enabled)
        self.alliance_detection_enabled = bool(alliance_detection_enabled)
        self.alliance_threshold = float(alliance_threshold)
        self.kingmaker_detection_enabled = bool(kingmaker_detection_enabled)
        self.kingmaker_score_gap = int(kingmaker_score_gap)
        self.adaptive_opponent_enabled = bool(adaptive_opponent_enabled)
        self.defensive_weight_shift = float(defensive_weight_shift)
        self._opponent_model: Optional[OpponentModelManager] = None

        # Layer 8 params
        if parallel_strategy not in {"root", "tree"}:
            raise ValueError(
                f"parallel_strategy must be 'root' or 'tree', got '{parallel_strategy}'"
            )
        self.num_workers = max(1, int(num_workers))
        self.virtual_loss = float(virtual_loss)
        self.parallel_strategy = parallel_strategy

        # Layer 9 params
        self.adaptive_exploration_enabled = bool(adaptive_exploration_enabled)
        self.adaptive_exploration_base = float(adaptive_exploration_base)
        self.adaptive_exploration_avg_bf = float(adaptive_exploration_avg_bf)
        self.adaptive_rollout_depth_enabled = bool(adaptive_rollout_depth_enabled)
        self.adaptive_rollout_depth_base = int(adaptive_rollout_depth_base)
        self.adaptive_rollout_depth_avg_bf = float(adaptive_rollout_depth_avg_bf)
        self.sufficiency_threshold_enabled = bool(sufficiency_threshold_enabled)
        self.loss_avoidance_enabled = bool(loss_avoidance_enabled)
        self.loss_avoidance_threshold = float(loss_avoidance_threshold)
        # Effective per-move values (set in select_action)
        self._effective_exploration_constant = float(
            adaptive_exploration_base if adaptive_exploration_enabled else exploration_constant
        )
        self._effective_rollout_cutoff_depth = rollout_cutoff_depth

        if self.potential_mode not in {"prob", "logit"}:
            raise ValueError("potential_mode must be either 'prob' or 'logit'.")
        if self.max_rollout_moves <= 0:
            raise ValueError("max_rollout_moves must be > 0.")

        self._requires_learned_evaluator = (
            self.leaf_evaluation_enabled
            or self.progressive_bias_enabled
            or self.potential_shaping_enabled
        )
        if self._requires_learned_evaluator and not self.learned_model_path:
            raise ValueError(
                "learned_model_path is required when learned evaluation, progressive bias, "
                "or potential shaping is enabled."
            )

        # Initialize components
        self.move_generator = get_shared_generator()
        self.piece_generator = PieceGenerator()
        self.zobrist_hash = ZobristHash(seed=seed)

        if rollout_agent is None:
            self.rollout_agent = HeuristicAgent(seed=seed)
        else:
            self.rollout_agent = rollout_agent

        if use_transposition_table:
            self.transposition_table = TranspositionTable()
        else:
            self.transposition_table = None

        self.learned_evaluator: Optional[LearnedWinProbabilityEvaluator] = None
        if self.learned_model_path:
            self.learned_evaluator = LearnedWinProbabilityEvaluator(
                self.learned_model_path,
                potential_mode=potential_mode,
            )

        # Layer 4: State evaluator for two-ply search and early termination
        # Layer 6: Phase-dependent weights override single weight vector
        self.state_evaluator = BlokusStateEvaluator(
            weights=state_eval_weights,
            phase_weights=state_eval_phase_weights,
        )
        # RNG for random rollout policy
        self._rng = np.random.RandomState(seed)
        # Track root player for minimax backups
        self._root_player: Optional[Player] = None

        # Progressive history table: {action_key: [total_reward, count]}
        # Persists across moves within a game.
        self._history_table: Dict[int, List[float]] = defaultdict(lambda: [0.0, 0])

        # Layer 5: NST (N-gram Selection Technique) table.
        # Key: (prev_action_key, current_action_key) — 2-gram of same-player moves.
        # Value: [total_reward, count]. Persists across moves within a game.
        self._nst_table: Dict[Tuple[int, int], List[float]] = defaultdict(lambda: [0.0, 0])
        # Track last action key played by root player (for NST continuity)
        self._last_root_action_key: Optional[int] = None

        # Statistics
        self.stats = {
            "iterations_run": 0,
            "time_elapsed": 0.0,
            "transposition_hits": 0,
            "rollout_rewards": [],
            "leaf_eval_calls": 0,
            "progressive_bias_updates": 0,
            "potential_shaping_terms": [],
            "evaluator_errors": 0,
            "pw_expansions_saved": 0,
            "history_table_size": 0,
            # Layer 4: Simulation strategy stats
            "two_ply_evals": 0,
            "cutoff_evals": 0,
            "minimax_updates": 0,
            # Layer 5: RAVE & NST stats
            "rave_updates": 0,
            "nst_rollout_biases": 0,
            # Layer 7: Opponent Modeling stats
            "opponent_random_rollouts": 0,
            "opponent_heuristic_rollouts": 0,
            "opponent_upgraded_rollouts": 0,
            "defensive_eval_adjustments": 0,
            # Layer 8: Parallelization stats
            "parallel_workers": 0,
            "parallel_strategy": "none",
            "parallel_trees_merged": 0,
            "virtual_loss_applications": 0,
            # Layer 9: Meta-Optimization stats
            "adaptive_c_value": 0.0,
            "adaptive_rollout_depth": 0,
            "sufficiency_activations": 0,
            "loss_avoidance_triggers": 0,
        }

        # Search Trace (Visualization)
        self.enable_search_trace = bool(enable_search_trace)
        self.search_trace_sample_rate = max(1, int(search_trace_sample_rate))
        self._search_trace: Optional[SearchTrace] = None
        self._trace_prev_best_key: Optional[str] = None
        self._trace_exploration_grid: Optional[List[List[int]]] = None

    def select_action(self, board: Board, player: Player, legal_moves: List[Move]) -> Optional[Move]:
        """
        Select action using MCTS.

        Args:
            board: Current board state
            player: Player making the move
            legal_moves: List of legal moves available

        Returns:
            Selected move, or None if no legal moves available
        """
        if not legal_moves:
            return None

        # If only one move, return it
        if len(legal_moves) == 1:
            return legal_moves[0]

        # Run MCTS
        start_time = time.time()
        self._root_player = player  # Layer 4: track for minimax backups

        # Layer 9: Compute adaptive per-move parameters
        if self.adaptive_exploration_enabled:
            bf = len(legal_moves)
            self._effective_exploration_constant = (
                self.adaptive_exploration_base
                * math.sqrt(bf / max(self.adaptive_exploration_avg_bf, 1.0))
            )
            self.stats["adaptive_c_value"] = self._effective_exploration_constant
        else:
            self._effective_exploration_constant = self.exploration_constant

        if self.adaptive_rollout_depth_enabled:
            bf = len(legal_moves)
            raw_depth = self.adaptive_rollout_depth_base * (
                self.adaptive_rollout_depth_avg_bf / max(bf, 1)
            )
            self._effective_rollout_cutoff_depth = max(1, int(round(raw_depth)))
            self.stats["adaptive_rollout_depth"] = self._effective_rollout_cutoff_depth
        else:
            self._effective_rollout_cutoff_depth = self.rollout_cutoff_depth

        # Layer 7: Initialize opponent model on first use
        if self.opponent_modeling_enabled and self._opponent_model is None:
            self._opponent_model = OpponentModelManager(
                root_player=player,
                alliance_detection_enabled=self.alliance_detection_enabled,
                alliance_threshold=self.alliance_threshold,
                kingmaker_detection_enabled=self.kingmaker_detection_enabled,
                kingmaker_score_gap=self.kingmaker_score_gap,
                adaptive_enabled=self.adaptive_opponent_enabled,
                defensive_weight_shift=self.defensive_weight_shift,
            )

        # Layer 8: Dispatch to parallel implementation when num_workers > 1
        if self.num_workers > 1 and self.parallel_strategy == "root":
            from .parallel import run_root_parallel

            best_move, par_stats = run_root_parallel(
                self, board, player, legal_moves, self.num_workers
            )
            self.stats["time_elapsed"] = time.time() - start_time
            self.stats["parallel_workers"] = self.num_workers
            self.stats["parallel_strategy"] = "root"
            self.stats["parallel_trees_merged"] = par_stats.get("trees_merged", 0)
            self.stats["iterations_run"] = par_stats.get("total_iterations", 0)
            if self.nst_enabled and best_move is not None:
                self._last_root_action_key = move_action_key(best_move)
            return best_move

        root = MCTSNode(board, player)

        # Initialize search trace if enabled
        if self.enable_search_trace:
            self._search_trace = SearchTrace(sample_rate=self.search_trace_sample_rate)
            self._trace_prev_best_key = None
            self._trace_exploration_grid = [[0] * 20 for _ in range(20)]

        # Heuristic move ordering: sort untried_moves so best are popped last
        if self.heuristic_move_ordering or self.progressive_widening_enabled:
            self._sort_untried_moves(root)

        # Layer 8: Tree parallelization with virtual loss
        if self.num_workers > 1 and self.parallel_strategy == "tree":
            self._run_mcts_tree_parallel(root)
        elif self.time_limit:
            self._run_mcts_with_time_limit(root)
        else:
            self._run_mcts_with_iterations(root)

        self.stats["time_elapsed"] = time.time() - start_time
        self.stats["history_table_size"] = len(self._history_table)
        if self.num_workers > 1:
            self.stats["parallel_workers"] = self.num_workers
            self.stats["parallel_strategy"] = self.parallel_strategy

        # Collect tree diagnostics before root is discarded
        self._collect_tree_diagnostics(root)

        # Finalize search trace before root is discarded
        if self.enable_search_trace and self._search_trace is not None:
            self._finalize_search_trace(root)

        # Get best move
        best_move = root.get_best_move()

        # Layer 5: Update NST last-action key for cross-move continuity
        if self.nst_enabled and best_move is not None:
            self._last_root_action_key = move_action_key(best_move)

        # Clean up transposition table if needed
        if self.transposition_table and len(self.transposition_table.table) > 500000:
            self.transposition_table.clear()

        return best_move

    def _sort_untried_moves(self, node: MCTSNode) -> None:
        """Sort a node's untried moves by heuristic score (ascending — best last)."""
        scored = rank_moves_by_heuristic(
            node.board, node.player, node.untried_moves, self.move_generator,
        )
        node.untried_moves = [m for _, m in scored]
        node._heuristic_sorted = True

    def _collect_tree_diagnostics(self, root: MCTSNode) -> None:
        """Walk the tree from root to collect diagnostic metrics.

        Populates ``self.stats`` with tree depth, size, entropy, Q-values,
        and regret gap so they are available via ``get_action_info()``.
        """
        # --- visit distribution entropy at root ---
        if root.children:
            visits = [child.visits for child in root.children]
            self.stats["visit_entropy"] = compute_policy_entropy(visits)
        else:
            self.stats["visit_entropy"] = 0.0

        # --- best and 2nd-best Q-values (regret gap) ---
        if root.children:
            q_values = []
            for child in root.children:
                if child.visits > 0:
                    q_values.append((child.total_reward / child.visits, child.visits, child))
            q_values.sort(key=lambda x: x[1], reverse=True)  # sort by visits (best move selection)

            if q_values:
                best_q, best_visits, _ = q_values[0]
                self.stats["best_move_q"] = best_q
                self.stats["best_move_visits"] = best_visits
                if len(q_values) > 1:
                    second_q = q_values[1][0]
                    self.stats["second_best_q"] = second_q
                    self.stats["regret_gap"] = best_q - second_q
                else:
                    self.stats["second_best_q"] = None
                    self.stats["regret_gap"] = None
            else:
                self.stats["best_move_q"] = None
                self.stats["best_move_visits"] = 0
                self.stats["second_best_q"] = None
                self.stats["regret_gap"] = None
        else:
            self.stats["best_move_q"] = None
            self.stats["best_move_visits"] = 0
            self.stats["second_best_q"] = None
            self.stats["regret_gap"] = None
            self.stats["visit_entropy"] = 0.0

        # --- tree size and depth via BFS ---
        total_nodes = 0
        max_depth = 0
        depth_sum = 0
        leaf_count = 0

        stack = [(root, 0)]
        while stack:
            node, depth = stack.pop()
            total_nodes += 1
            if not node.children:
                leaf_count += 1
                depth_sum += depth
                if depth > max_depth:
                    max_depth = depth
            else:
                for child in node.children:
                    stack.append((child, depth + 1))

        mean_depth = depth_sum / leaf_count if leaf_count > 0 else 0.0

        self.stats["tree_size"] = total_nodes
        self.stats["tree_depth_max"] = max_depth
        self.stats["tree_depth_mean"] = mean_depth
        self.stats["branching_factor"] = len(root.untried_moves) + len(root.children)

    # --- Search Trace helpers ---

    def _selection_traced(self, node: MCTSNode):
        """Selection with UCT term tracking for search trace.

        Returns (selected_node, selection_depth, avg_exploitation, avg_exploration).
        """
        pw_bias_w = self.progressive_bias_weight if self.progressive_bias_enabled else 0.0
        ph_w = self.progressive_history_weight if self.progressive_history_enabled else 0.0
        hist = self._history_table if self.progressive_history_enabled else None
        mm_alpha = self.minimax_backup_alpha
        rave_on = self.rave_enabled
        rave_k_val = self.rave_k
        la = self.loss_avoidance_enabled

        depth = 0
        exploit_sum = 0.0
        explore_sum = 0.0
        steps = 0

        while not node.is_terminal():
            if self.progressive_widening_enabled:
                if node.should_expand_pw(self.pw_c, self.pw_alpha):
                    break
                if node.children:
                    # Compute UCT terms for the chosen child
                    chosen = node.select_child(
                        exploration_constant=self._effective_exploration_constant,
                        progressive_bias_weight=pw_bias_w,
                        progressive_history_weight=ph_w,
                        history_table=hist,
                        minimax_alpha=mm_alpha,
                        rave_enabled=rave_on,
                        rave_k=rave_k_val,
                        loss_avoidance=la,
                    )
                    if chosen.visits > 0 and node.visits > 0:
                        exploit_sum += chosen.blended_q(mm_alpha)
                        explore_sum += self._effective_exploration_constant * math.sqrt(
                            math.log(node.visits) / chosen.visits
                        )
                        steps += 1
                    node = chosen
                    depth += 1
                else:
                    break
            else:
                if not node.is_fully_expanded():
                    break
                chosen = node.select_child(
                    exploration_constant=self._effective_exploration_constant,
                    progressive_bias_weight=pw_bias_w,
                    progressive_history_weight=ph_w,
                    history_table=hist,
                    minimax_alpha=mm_alpha,
                    rave_enabled=rave_on,
                    rave_k=rave_k_val,
                    loss_avoidance=la,
                )
                if chosen.visits > 0 and node.visits > 0:
                    exploit_sum += chosen.blended_q(mm_alpha)
                    explore_sum += self._effective_exploration_constant * math.sqrt(
                        math.log(node.visits) / chosen.visits
                    )
                    steps += 1
                node = chosen
                depth += 1

        avg_exploit = exploit_sum / steps if steps > 0 else 0.0
        avg_explore = explore_sum / steps if steps > 0 else 0.0
        return node, depth, avg_exploit, avg_explore

    def _snapshot_root_children(self, root: MCTSNode, iteration: int) -> None:
        """Capture root children stats for a search trace checkpoint."""
        if not self._search_trace or not root.children:
            return
        total_visits = sum(c.visits for c in root.children)
        children = []
        for c in sorted(root.children, key=lambda x: x.visits, reverse=True)[:20]:
            if c.move is None or c.visits == 0:
                continue
            m = c.move
            children.append(RootChildSnapshot(
                action_id=f"{m.piece_id}:{m.orientation}@{m.anchor_row},{m.anchor_col}",
                piece_id=m.piece_id,
                orientation=m.orientation,
                anchor_row=m.anchor_row,
                anchor_col=m.anchor_col,
                visits=c.visits,
                q_value=c.total_reward / c.visits,
                probability=c.visits / total_visits if total_visits > 0 else 0.0,
            ))
        self._search_trace.root_snapshots.append(
            RootSnapshotCheckpoint(iteration=iteration, children=children)
        )

    def _finalize_search_trace(self, root: MCTSNode) -> None:
        """Compute final UCT breakdown and exploration grid for the trace."""
        trace = self._search_trace
        if trace is None:
            return

        # UCT breakdown for root children
        if root.children and root.visits > 0:
            mm_alpha = self.minimax_backup_alpha
            parent_visits = root.visits
            rave_on = self.rave_enabled
            rave_k_val = self.rave_k

            r_beta = 0.0
            if rave_on and parent_visits > 0:
                r_beta = math.sqrt(rave_k_val / (3.0 * parent_visits + rave_k_val))

            for child in sorted(root.children, key=lambda x: x.visits, reverse=True)[:20]:
                if child.move is None or child.visits == 0:
                    continue
                m = child.move
                exploitation = child.blended_q(mm_alpha)
                exploration = self._effective_exploration_constant * math.sqrt(
                    math.log(parent_visits) / child.visits
                )

                child_rave_q = 0.0
                child_rave_beta = 0.0
                if r_beta > 0.0 and child.move is not None:
                    akey = move_action_key(child.move)
                    rv = root.rave_visits.get(akey, 0)
                    if rv > 0:
                        child_rave_q = root.rave_total[akey] / rv
                        child_rave_beta = r_beta

                total = exploitation + exploration
                if child_rave_beta > 0:
                    blended_exploit = (1.0 - child_rave_beta) * exploitation + child_rave_beta * child_rave_q
                    total = blended_exploit + exploration

                trace.uct_breakdown.append(UctChildBreakdown(
                    action_id=f"{m.piece_id}:{m.orientation}@{m.anchor_row},{m.anchor_col}",
                    piece_id=m.piece_id,
                    orientation=m.orientation,
                    anchor_row=m.anchor_row,
                    anchor_col=m.anchor_col,
                    visits=child.visits,
                    parent_visits=parent_visits,
                    exploitation=exploitation,
                    exploration=exploration,
                    rave_q=child_rave_q,
                    rave_beta=child_rave_beta,
                    total=total,
                ))

        # Attach exploration grid
        trace.exploration_grid = self._trace_exploration_grid

    def _track_explored_move(self, move: Move) -> None:
        """Increment exploration grid cells for an expanded move."""
        grid = self._trace_exploration_grid
        if grid is None:
            return
        orientations = self.move_generator.piece_orientations_cache[move.piece_id]
        orientation = orientations[move.orientation]
        rows, cols = orientation.shape
        for i in range(rows):
            for j in range(cols):
                if orientation[i, j] == 1:
                    r, c = move.anchor_row + i, move.anchor_col + j
                    if 0 <= r < 20 and 0 <= c < 20:
                        grid[r][c] += 1

    def _quick_max_depth(self, root: MCTSNode) -> int:
        """Fast max depth estimate using DFS limited to first few branches."""
        max_d = 0
        stack = [(root, 0)]
        nodes_checked = 0
        while stack and nodes_checked < 500:
            node, d = stack.pop()
            nodes_checked += 1
            if d > max_d:
                max_d = d
            # Only follow the most-visited children to stay fast
            for child in node.children[:3]:
                stack.append((child, d + 1))
        return max_d

    def _quick_tree_size(self, root: MCTSNode) -> int:
        """Fast tree size estimate using BFS limited to 1000 nodes."""
        count = 0
        stack = [root]
        while stack and count < 1000:
            node = stack.pop()
            count += 1
            stack.extend(node.children)
        return count

    def _root_best_key(self, root: MCTSNode) -> Optional[str]:
        """Return action key string for the current best root child."""
        if not root.children:
            return None
        best = max(root.children, key=lambda c: c.visits)
        if best.move is None:
            return None
        m = best.move
        return f"{m.piece_id}:{m.orientation}@{m.anchor_row},{m.anchor_col}"

    def get_search_trace(self) -> Optional[Dict[str, Any]]:
        """Return the search trace from the last move as a JSON-serializable dict."""
        if self._search_trace is None:
            return None
        return self._search_trace.to_dict()

    def _run_mcts_with_iterations(self, root: MCTSNode):
        """Run MCTS for specified number of iterations."""
        sufficiency_checked = False
        warmup = self.iterations // 3 if self.sufficiency_threshold_enabled else -1
        trace = self._search_trace
        sample_rate = self.search_trace_sample_rate if trace else 0
        # Snapshot checkpoints at 10%, 25%, 50%, 75%, 100%
        snapshot_iters = set()
        if trace:
            for pct in (0.10, 0.25, 0.50, 0.75, 1.0):
                snapshot_iters.add(max(0, int(self.iterations * pct) - 1))
        for i in range(self.iterations):
            self._mcts_iteration(root, iteration_idx=i)
            self.stats["iterations_run"] = i + 1
            # Search trace: snapshot root children at checkpoints
            if trace and i in snapshot_iters:
                self._snapshot_root_children(root, i)
            # Layer 9: Sufficiency threshold — after warmup, check if any child
            # Q-value exceeds mean+stddev. If so, switch to pure exploitation.
            if not sufficiency_checked and i == warmup:
                sufficiency_checked = True
                self._check_sufficiency_threshold(root)
        if trace:
            trace.total_iterations = self.iterations

    def _run_mcts_with_time_limit(self, root: MCTSNode):
        """Run MCTS for specified time limit."""
        start_time = time.time()
        iteration = 0
        sufficiency_checked = False
        warmup_time = self.time_limit / 3.0 if self.sufficiency_threshold_enabled else float('inf')
        trace = self._search_trace
        # For time-limited, snapshot at time fractions
        next_snapshot_pct_idx = 0
        snapshot_pcts = [0.10, 0.25, 0.50, 0.75, 1.0]

        while time.time() - start_time < self.time_limit:
            self._mcts_iteration(root, iteration_idx=iteration)
            iteration += 1
            # Snapshot at time percentage checkpoints
            if trace and next_snapshot_pct_idx < len(snapshot_pcts):
                elapsed_frac = (time.time() - start_time) / self.time_limit
                if elapsed_frac >= snapshot_pcts[next_snapshot_pct_idx]:
                    self._snapshot_root_children(root, iteration)
                    next_snapshot_pct_idx += 1
            if not sufficiency_checked and time.time() - start_time >= warmup_time:
                sufficiency_checked = True
                self._check_sufficiency_threshold(root)

        self.stats["iterations_run"] = iteration
        if trace:
            # Final snapshot if not yet taken
            if next_snapshot_pct_idx < len(snapshot_pcts):
                self._snapshot_root_children(root, iteration)
            trace.total_iterations = iteration

    def _check_sufficiency_threshold(self, root: MCTSNode) -> None:
        """Layer 9: If any root child Q-value exceeds mean + stddev, switch to C=0."""
        visited = [c for c in root.children if c.visits > 0]
        if len(visited) < 2:
            return
        q_vals = [c.total_reward / c.visits for c in visited]
        mean_q = sum(q_vals) / len(q_vals)
        variance = sum((q - mean_q) ** 2 for q in q_vals) / len(q_vals)
        std_q = variance ** 0.5
        alpha = mean_q + std_q
        if any(q > alpha for q in q_vals):
            self._effective_exploration_constant = 0.0
            self.stats["sufficiency_activations"] = 1

    def _run_mcts_tree_parallel(self, root: MCTSNode):
        """Run tree-parallel MCTS with virtual loss using threads.

        Layer 8: Multiple threads share a single tree. Virtual loss prevents
        threads from selecting the same path simultaneously — when a thread
        enters a node during selection, it applies a virtual loss penalty that
        reduces the node's UCB score for other threads.

        Note: Due to CPython's GIL, this does not provide true CPU parallelism.
        It demonstrates the correct algorithm and is ready for free-threaded
        Python (3.13+).
        """
        import threading

        expand_lock = threading.Lock()
        iterations_per_worker = max(1, self.iterations // self.num_workers)
        total_iterations = [0]
        total_vl = [0]
        count_lock = threading.Lock()

        def worker():
            local_iters = 0
            local_vl = 0
            for _ in range(iterations_per_worker):
                # Selection with virtual loss
                node, vl_path = self._selection_with_virtual_loss(root)
                local_vl += len(vl_path)

                # Expansion (under lock to prevent duplicate children)
                expanded = False
                with expand_lock:
                    expand = False
                    if self.progressive_widening_enabled:
                        if node.should_expand_pw(self.pw_c, self.pw_alpha):
                            expand = True
                    else:
                        expand = not node.is_fully_expanded() and not node.is_terminal()
                    if expand:
                        if (self.heuristic_move_ordering or self.progressive_widening_enabled) and not node._heuristic_sorted:
                            self._sort_untried_moves(node)
                        child = node.expand()
                        if child is not None:
                            self._update_progressive_bias(node, child)
                            node = child
                            expanded = True

                # Simulation (no lock — each thread simulates independently)
                reward, rollout_actions = self._simulation(node)

                # Remove virtual losses from selection path
                for vl_node in vl_path:
                    vl_node.remove_virtual_loss(self.virtual_loss)

                # Backpropagation (minor races on node.visits/total_reward are
                # tolerable — standard in MCTS literature)
                self._backpropagation(node, reward, rollout_actions=rollout_actions)
                local_iters += 1

            with count_lock:
                total_iterations[0] += local_iters
                total_vl[0] += local_vl

        threads = [threading.Thread(target=worker) for _ in range(self.num_workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.stats["iterations_run"] = total_iterations[0]
        self.stats["virtual_loss_applications"] = total_vl[0]

    def _selection_with_virtual_loss(self, root: MCTSNode):
        """Selection phase with virtual loss for tree parallelization.

        Same as _selection but applies virtual loss at each visited node
        to discourage other threads from the same path.

        Returns:
            Tuple of (selected_node, list_of_nodes_with_virtual_loss)
        """
        vl_path = []
        node = root

        pw_bias_w = self.progressive_bias_weight if self.progressive_bias_enabled else 0.0
        ph_w = self.progressive_history_weight if self.progressive_history_enabled else 0.0
        hist = self._history_table if self.progressive_history_enabled else None
        mm_alpha = self.minimax_backup_alpha
        rave_on = self.rave_enabled
        rave_k = self.rave_k
        la = self.loss_avoidance_enabled

        while not node.is_terminal():
            if self.progressive_widening_enabled:
                if node.should_expand_pw(self.pw_c, self.pw_alpha):
                    return node, vl_path
                if node.children:
                    node.apply_virtual_loss(self.virtual_loss)
                    vl_path.append(node)
                    node = node.select_child(
                        exploration_constant=self._effective_exploration_constant,
                        progressive_bias_weight=pw_bias_w,
                        progressive_history_weight=ph_w,
                        history_table=hist,
                        minimax_alpha=mm_alpha,
                        rave_enabled=rave_on,
                        rave_k=rave_k,
                        loss_avoidance=la,
                    )
                else:
                    return node, vl_path
            else:
                if not node.is_fully_expanded():
                    return node, vl_path
                node.apply_virtual_loss(self.virtual_loss)
                vl_path.append(node)
                node = node.select_child(
                    exploration_constant=self._effective_exploration_constant,
                    progressive_bias_weight=pw_bias_w,
                    progressive_history_weight=ph_w,
                    history_table=hist,
                    minimax_alpha=mm_alpha,
                    rave_enabled=rave_on,
                    rave_k=rave_k,
                    loss_avoidance=la,
                )

        return node, vl_path

    def _mcts_iteration(self, root: MCTSNode, iteration_idx: int = 0):
        """
        Run one MCTS iteration.

        Args:
            root: Root node of the search tree
            iteration_idx: Current iteration index (for trace sampling)
        """
        trace = self._search_trace

        # Selection: traverse tree using UCB1
        if trace:
            node, sel_depth, avg_exploit, avg_explore = self._selection_traced(root)
        else:
            node = self._selection(root)

        # Expansion: expand node if allowed
        expand = False
        expanded_depth = 0
        if self.progressive_widening_enabled:
            # Progressive widening: expand only if child count < C_pw * N^alpha
            if node.should_expand_pw(self.pw_c, self.pw_alpha):
                expand = True
            elif not node.untried_moves and not node.children:
                # Terminal: no moves at all
                pass
            else:
                self.stats["pw_expansions_saved"] += 1
        else:
            # Standard MCTS: expand if not fully expanded
            expand = not node.is_fully_expanded() and not node.is_terminal()

        if expand:
            parent = node
            # Sort child moves on first expansion if not done yet
            if (self.heuristic_move_ordering or self.progressive_widening_enabled) and not node._heuristic_sorted:
                self._sort_untried_moves(node)
            node = node.expand()
            if node is None:
                return
            self._update_progressive_bias(parent, node)

            # Track explored cells for heatmap
            if trace and self._trace_exploration_grid is not None and node.move is not None:
                self._track_explored_move(node.move)

            # Count expanded depth
            if trace:
                d = node
                while d.parent is not None:
                    expanded_depth += 1
                    d = d.parent

        # Simulation: run rollout (returns rollout action keys when RAVE enabled)
        reward, rollout_actions = self._simulation(node)

        # Record rollout result for trace
        if trace:
            trace.rollout_results.append(round(reward, 4))

        # Backpropagation: update statistics up the tree
        self._backpropagation(node, reward, rollout_actions=rollout_actions)

        # Sample iteration record for time-series
        if trace and iteration_idx % trace.sample_rate == 0:
            # Compute quick tree stats
            max_depth = self._quick_max_depth(root)
            tree_size = self._quick_tree_size(root)
            # Check if best move changed
            best_key = self._root_best_key(root)
            changed = best_key != self._trace_prev_best_key
            self._trace_prev_best_key = best_key

            record = IterationRecord(
                iteration=iteration_idx,
                selected_depth=sel_depth if trace else 0,
                expanded_depth=expanded_depth,
                max_tree_depth=max_depth,
                tree_size=tree_size,
                root_children_count=len(root.children),
                avg_branching=tree_size / max(len(root.children), 1),
                exploitation_term=avg_exploit if trace else 0.0,
                exploration_term=avg_explore if trace else 0.0,
                best_move_changed=changed,
            )
            trace.iteration_records.append(record)

    def _selection(self, node: MCTSNode) -> MCTSNode:
        """
        Selection phase: traverse tree using UCB1 + progressive history + RAVE.

        With progressive widening, a node is "expandable" when
        len(children) < C_pw * visits^alpha AND untried_moves remain.

        Args:
            node: Starting node

        Returns:
            Selected node
        """
        pw_bias_w = self.progressive_bias_weight if self.progressive_bias_enabled else 0.0
        ph_w = self.progressive_history_weight if self.progressive_history_enabled else 0.0
        hist = self._history_table if self.progressive_history_enabled else None
        mm_alpha = self.minimax_backup_alpha
        rave_on = self.rave_enabled
        rave_k = self.rave_k
        la = self.loss_avoidance_enabled

        while not node.is_terminal():
            if self.progressive_widening_enabled:
                # With PW: return node for expansion if widening allows
                if node.should_expand_pw(self.pw_c, self.pw_alpha):
                    return node
                # Otherwise, if there are children, select among them
                if node.children:
                    node = node.select_child(
                        exploration_constant=self._effective_exploration_constant,
                        progressive_bias_weight=pw_bias_w,
                        progressive_history_weight=ph_w,
                        history_table=hist,
                        minimax_alpha=mm_alpha,
                        rave_enabled=rave_on,
                        rave_k=rave_k,
                        loss_avoidance=la,
                    )
                else:
                    return node
            else:
                # Standard MCTS
                if not node.is_fully_expanded():
                    return node
                node = node.select_child(
                    exploration_constant=self._effective_exploration_constant,
                    progressive_bias_weight=pw_bias_w,
                    progressive_history_weight=ph_w,
                    history_table=hist,
                    minimax_alpha=mm_alpha,
                    rave_enabled=rave_on,
                    rave_k=rave_k,
                    loss_avoidance=la,
                )

        return node

    def _simulation(self, node: MCTSNode) -> Tuple[float, List[int]]:
        """
        Simulation phase: run rollout from node.

        Args:
            node: Node to simulate from

        Returns:
            Tuple of (reward, rollout_action_keys). The action key list
            contains piece_ids played by the root player during the rollout,
            used for RAVE updates. Empty when RAVE is disabled or on cache hit.
        """
        # Check transposition table
        if self.transposition_table:
            board_hash = self.zobrist_hash.hash_board(node.board)
            cached_result = self.transposition_table.get(board_hash)
            if cached_result:
                self.stats["transposition_hits"] += 1
                return cached_result["reward"], []

        # Run learned leaf evaluation or rollout.
        rollout_actions: List[int] = []
        if self.leaf_evaluation_enabled and self.learned_evaluator is not None:
            reward = self._evaluate_leaf(node.board, node.player)
        else:
            reward, rollout_actions = self._rollout(node.board, node.player)

        # Cache result
        if self.transposition_table:
            self.transposition_table.put(board_hash, {"reward": reward})

        self.stats["rollout_rewards"].append(reward)
        return reward, rollout_actions

    def _evaluate_leaf(self, board: Board, player: Player) -> float:
        """Evaluate leaf with learned model-backed win probability.

        Uses root player perspective for consistent reward semantics.
        """
        if self.learned_evaluator is None:
            return self._rollout(board, player)
        reward_player = self._root_player if self._root_player is not None else player
        try:
            probability = self.learned_evaluator.predict_player_win_probability(
                board, reward_player
            )
            self.stats["leaf_eval_calls"] += 1
            return float(probability)
        except Exception:
            self.stats["evaluator_errors"] += 1
            return self._rollout(board, player)

    def _update_progressive_bias(self, parent: MCTSNode, child: MCTSNode) -> None:
        """Set child prior bias from learned value delta."""
        if not self.progressive_bias_enabled or self.learned_evaluator is None:
            return
        try:
            parent_value = self.learned_evaluator.predict_player_win_probability(
                parent.board, parent.player
            )
            child_value = self.learned_evaluator.predict_player_win_probability(
                child.board, parent.player
            )
            child.prior_bias = float(child_value - parent_value)
            self.stats["progressive_bias_updates"] += 1
        except Exception:
            child.prior_bias = 0.0
            self.stats["evaluator_errors"] += 1

    def _rollout(self, board: Board, player: Player) -> Tuple[float, List[int]]:
        """
        Run rollout simulation with configurable policy and early termination.

        All rewards are computed from the root player's perspective so that
        backpropagation can propagate a single consistent value up the tree.

        Layer 4 enhancements:
        - rollout_policy: "heuristic" (default), "random", or "two_ply"
        - rollout_cutoff_depth: terminate early and evaluate statically

        Layer 5: When RAVE is enabled, collects action keys (piece_ids) played
        by the root player during the rollout for RAVE back-propagation.

        Args:
            board: Board state to simulate from
            player: Player whose turn it is

        Returns:
            Tuple of (reward, rollout_action_keys)
        """
        # All rewards must be from the root player's perspective.
        reward_player = self._root_player if self._root_player is not None else player

        # Layer 7: Get defensive weight adjustments from opponent model
        defensive_adj = self._get_defensive_adjustments(board)

        # Layer 4: depth-0 cutoff — pure static evaluation, no rollout at all
        if self._effective_rollout_cutoff_depth is not None and self._effective_rollout_cutoff_depth <= 0:
            self.stats["cutoff_evals"] += 1
            return self.state_evaluator.evaluate(board, reward_player, defensive_adj) * self._eval_reward_scale, []

        # Create copy for simulation
        sim_board = board.copy()
        current_player = player

        # Get initial score from root player's perspective
        initial_score = sim_board.get_score(reward_player)
        initial_potential = None
        if self.potential_shaping_enabled and self.learned_evaluator is not None:
            try:
                initial_potential = self.learned_evaluator.potential(sim_board, reward_player)
            except Exception:
                self.stats["evaluator_errors"] += 1
                initial_potential = None

        # Layer 5: Track root player's moves for RAVE and NST
        root_player = self._root_player
        track_rave = self.rave_enabled and root_player is not None
        track_nst = self.nst_enabled and root_player is not None
        rollout_actions: List[int] = []
        # NST: track root player's previous action key within this rollout
        nst_prev_own_key: Optional[int] = self._last_root_action_key if track_nst else None

        # Simulate until game ends or max moves
        moves_made = 0
        consecutive_passes = 0
        num_players = len(_PLAYERS)

        while moves_made < self.max_rollout_moves:
            # Layer 4: Early termination at cutoff depth
            if (
                self._effective_rollout_cutoff_depth is not None
                and moves_made >= self._effective_rollout_cutoff_depth
            ):
                self.stats["cutoff_evals"] += 1
                return (
                    self.state_evaluator.evaluate(sim_board, reward_player, defensive_adj) * self._eval_reward_scale,
                    rollout_actions,
                )

            # Get legal moves
            legal_moves = self.move_generator.get_legal_moves(sim_board, current_player)

            if not legal_moves:
                # Player passes — advance to next player
                consecutive_passes += 1
                if consecutive_passes >= num_players:
                    # All players passed consecutively — game is truly over
                    break
                current_idx = _PLAYERS.index(current_player)
                current_player = _PLAYERS[(current_idx + 1) % num_players]
                continue

            # Layer 5: NST-biased move selection for root player
            if (
                track_nst
                and current_player == root_player
                and nst_prev_own_key is not None
                and len(legal_moves) > 1
            ):
                move = self._nst_biased_select(legal_moves, nst_prev_own_key)
            elif current_player == root_player:
                # Self: use configured rollout_policy
                if self.rollout_policy == "two_ply":
                    move = self._two_ply_select(sim_board, current_player, legal_moves)
                elif self.rollout_policy == "random":
                    move = legal_moves[self._rng.randint(len(legal_moves))]
                else:
                    move = self.rollout_agent.select_action(sim_board, current_player, legal_moves)
            else:
                # Layer 7: Opponent — use opponent rollout policy (possibly upgraded).
                # When opponent_rollout_policy=="same", _select_opponent_rollout_move
                # resolves "same" to the root player's rollout_policy but still
                # allows the opponent model to upgrade individual opponents.
                move = self._select_opponent_rollout_move(
                    sim_board, current_player, legal_moves
                )

            if move is None:
                break

            # Layer 5: Record root player's moves for RAVE and NST
            if current_player == root_player:
                akey = move_action_key(move)
                if track_rave:
                    rollout_actions.append(akey)
                if track_nst:
                    nst_prev_own_key = akey

            # Make move
            move_positions = self._get_move_positions(move)
            success = sim_board.place_piece(move_positions, current_player, move.piece_id, validate=False)

            if not success:
                break

            # Successful move resets consecutive pass counter
            consecutive_passes = 0

            # Move to next player
            current_idx = _PLAYERS.index(current_player)
            current_player = _PLAYERS[(current_idx + 1) % num_players]
            moves_made += 1

        # Calculate reward from root player's perspective
        final_score = sim_board.get_score(reward_player)
        reward = final_score - initial_score

        # Add bonus for winning (from root player's perspective)
        if sim_board.is_game_over():
            winner = sim_board.get_winner()
            if winner == reward_player:
                reward += 100
            elif winner is None:
                reward += 10

        # Apply potential-based shaping only on truncated rollouts.
        if (
            self.potential_shaping_enabled
            and self.learned_evaluator is not None
            and initial_potential is not None
            and moves_made >= self.max_rollout_moves
            and not sim_board.is_game_over()
        ):
            try:
                final_potential = self.learned_evaluator.potential(sim_board, reward_player)
                shaping_term = self.potential_shaping_weight * (
                    (self.potential_shaping_gamma * final_potential) - initial_potential
                )
                reward += shaping_term
                if len(self.stats["potential_shaping_terms"]) < 2048:
                    self.stats["potential_shaping_terms"].append(float(shaping_term))
            except Exception:
                self.stats["evaluator_errors"] += 1

        return reward, rollout_actions

    def _two_ply_select(
        self, board: Board, player: Player, legal_moves: List[Move]
    ) -> Move:
        """Select a rollout move using two-ply max-n search.

        For each candidate move, apply it and evaluate the resulting state.
        Return the move that maximises the state evaluation for *player*.

        When ``two_ply_top_k`` is set, only the top-K moves (by heuristic
        score) are evaluated, trading some quality for throughput.

        Args:
            board: Current board state
            player: Player to move
            legal_moves: Available legal moves

        Returns:
            Best move according to one-ply lookahead evaluation
        """
        candidates = legal_moves
        if self.two_ply_top_k is not None and len(candidates) > self.two_ply_top_k:
            scored = rank_moves_by_heuristic(
                board, player, candidates, self.move_generator
            )
            # Best moves are at the end (ascending sort)
            candidates = [m for _, m in scored[-self.two_ply_top_k:]]

        best_move = candidates[0]
        best_value = float('-inf')

        for move in candidates:
            sim = board.copy()
            positions = self._get_move_positions(move)
            sim.place_piece(positions, player, move.piece_id, validate=False)
            value = self.state_evaluator.evaluate(
                sim, player, self._get_defensive_adjustments(board)
            )
            if value > best_value:
                best_value = value
                best_move = move

        self.stats["two_ply_evals"] += len(candidates)
        return best_move

    def _nst_biased_select(
        self, legal_moves: List[Move], prev_action_key: int
    ) -> Move:
        """Select a rollout move biased by NST 2-gram statistics.

        Computes a softmax-weighted distribution over legal moves using the
        NST table score for the (prev_action_key, candidate_key) pair.
        Falls back to uniform random if no NST data exists.

        Args:
            legal_moves: Available legal moves
            prev_action_key: The root player's previous action key

        Returns:
            Selected move
        """
        scores = []
        has_data = False
        for move in legal_moves:
            ckey = move_action_key(move)
            entry = self._nst_table.get((prev_action_key, ckey))
            if entry is not None and entry[1] > 0:
                scores.append(entry[0] / entry[1])
                has_data = True
            else:
                scores.append(0.0)

        if not has_data:
            # No NST data — fall back to random
            return legal_moves[self._rng.randint(len(legal_moves))]

        # Softmax with temperature = nst_weight
        scores_arr = np.array(scores, dtype=np.float64)
        # Shift for numerical stability
        scores_arr -= scores_arr.max()
        weights = np.exp(scores_arr * self.nst_weight)
        weights /= weights.sum()
        idx = self._rng.choice(len(legal_moves), p=weights)
        self.stats["nst_rollout_biases"] += 1
        return legal_moves[idx]

    def _get_move_positions(self, move: Move) -> List[Position]:
        """Get positions that a move would occupy."""
        orientations = self.move_generator.piece_orientations_cache[move.piece_id]
        orientation = orientations[move.orientation]

        positions = []
        rows, cols = orientation.shape

        for i in range(rows):
            for j in range(cols):
                if orientation[i, j] == 1:
                    pos = Position(move.anchor_row + i, move.anchor_col + j)
                    positions.append(pos)

        return positions

    # ------------------------------------------------------------------
    # Layer 7: Defensive evaluation adjustments
    # ------------------------------------------------------------------

    def _get_defensive_adjustments(self, board: Board) -> Optional[Dict[str, float]]:
        """Return weight adjustments from opponent model, or None.

        When an opponent is flagged as targeting the root player, the opponent
        model returns weight deltas that shift evaluation toward defensive
        features.  Returns None when no adjustment is needed (the common case).
        """
        if self._opponent_model is None:
            return None
        adj = self._opponent_model.get_defensive_eval_adjustment(board)
        if adj:
            self.stats["defensive_eval_adjustments"] += 1
            return adj
        return None

    # ------------------------------------------------------------------
    # Layer 7: Opponent rollout and move notification
    # ------------------------------------------------------------------

    def _select_opponent_rollout_move(
        self, board: Board, player: Player, legal_moves: List[Move]
    ) -> Move:
        """Select a rollout move for an opponent player.

        Uses ``opponent_rollout_policy`` as the base, but may upgrade to
        heuristic if the opponent model flags the player as targeting or
        king-making.

        Args:
            board: Current simulation board state.
            player: Opponent player to move.
            legal_moves: Available legal moves.

        Returns:
            Selected move for the opponent.
        """
        # Resolve "same" to the root player's rollout_policy so the
        # opponent model can still upgrade individual opponents.
        policy = self.opponent_rollout_policy
        if policy == "same":
            policy = self.rollout_policy

        base_policy = policy

        # Allow the opponent model to override the policy per-player
        if self._opponent_model is not None:
            policy = self._opponent_model.get_opponent_rollout_policy(
                player, policy
            )
            if policy != base_policy:
                self.stats["opponent_upgraded_rollouts"] += 1

        if policy == "random":
            self.stats["opponent_random_rollouts"] += 1
            return legal_moves[self._rng.randint(len(legal_moves))]
        elif policy == "two_ply":
            return self._two_ply_select(board, player, legal_moves)
        else:
            # "heuristic" (or fallback)
            self.stats["opponent_heuristic_rollouts"] += 1
            return self.rollout_agent.select_action(board, player, legal_moves)

    def notify_move(
        self,
        board_before: Board,
        board_after: Board,
        player: Player,
    ) -> None:
        """Notify the agent that a move was made in the actual game.

        Called by the arena runner after each move to update blocking
        tracking and alliance detection. Only has an effect when
        ``opponent_modeling_enabled`` is True.

        Args:
            board_before: Board state before the move.
            board_after: Board state after the move.
            player: Player who made the move.
        """
        if self._opponent_model is not None:
            self._opponent_model.on_move_made(board_before, board_after, player)

    def reset_opponent_model_game(self) -> None:
        """Reset per-game opponent tracking. Profiles persist across games."""
        if self._opponent_model is not None:
            self._opponent_model.reset_game()

    def get_opponent_model_stats(self) -> Dict[str, Any]:
        """Return opponent model diagnostics."""
        if self._opponent_model is not None:
            return self._opponent_model.get_stats()
        return {}

    def _backpropagation(
        self,
        node: MCTSNode,
        reward: float,
        rollout_actions: Optional[List[int]] = None,
    ):
        """
        Backpropagation phase: update statistics up the tree.

        Also updates the progressive history table with move performance,
        implicit minimax values when minimax_backup_alpha > 0, and per-node
        RAVE tables when rave_enabled is True.

        Args:
            node: Node to start backpropagation from
            reward: Reward to propagate
            rollout_actions: Action keys (piece_ids) played by root player
                during rollout, for RAVE updates (Layer 5)
        """
        use_minimax = self.minimax_backup_alpha > 0.0
        root_player = self._root_player

        # Layer 5: Build the full set of action keys seen in the simulation.
        # As we walk up the tree, we collect tree-move action keys and combine
        # them with rollout actions. Each node gets RAVE updates for all
        # actions seen *below* it.
        use_rave = self.rave_enabled and rollout_actions is not None
        if use_rave:
            # Start with rollout actions as a set
            rave_action_set: set = set(rollout_actions)
        else:
            rave_action_set = set()

        # Layer 9: Loss avoidance — mark nodes that led to catastrophic results
        use_loss_avoidance = (
            self.loss_avoidance_enabled and reward < self.loss_avoidance_threshold
        )

        while node is not None:
            node.update(reward)

            # Layer 9: Flag this node so selection prefers siblings next time
            if use_loss_avoidance and node.parent is not None:
                node.loss_detected = True
                self.stats["loss_avoidance_triggers"] += 1

            # Update progressive history for the move that led to this node
            if self.progressive_history_enabled and node.move is not None:
                key = move_action_key(node.move)
                entry = self._history_table[key]
                entry[0] += reward
                entry[1] += 1

            # Layer 5: Update RAVE tables at this node for all actions below
            if use_rave and rave_action_set:
                for akey in rave_action_set:
                    if akey in node.rave_visits:
                        node.rave_total[akey] += reward
                        node.rave_visits[akey] += 1
                    else:
                        node.rave_total[akey] = reward
                        node.rave_visits[akey] = 1
                self.stats["rave_updates"] += 1
                # Add this node's own move to the set so that ancestors
                # see it as part of the "actions below"
                if node.move is not None:
                    rave_action_set.add(move_action_key(node.move))

            # Layer 4: Update implicit minimax values
            if use_minimax and node.children:
                visited_children_q = [
                    c.total_reward / c.visits
                    for c in node.children
                    if c.visits > 0
                ]
                if visited_children_q:
                    if node.player == root_player:
                        # Root player maximises
                        node.minimax_value = max(visited_children_q)
                    else:
                        # Opponents minimise (from root's perspective)
                        node.minimax_value = min(visited_children_q)
                    self.stats["minimax_updates"] += 1
            node = node.parent

        # Layer 5: Update NST 2-gram table from rollout action sequence.
        # rollout_actions is the sequence of root player's action keys.
        if self.nst_enabled and rollout_actions and len(rollout_actions) >= 2:
            prev_key = self._last_root_action_key
            for akey in rollout_actions:
                if prev_key is not None:
                    entry = self._nst_table[(prev_key, akey)]
                    entry[0] += reward
                    entry[1] += 1
                prev_key = akey

    def get_action_info(self) -> Dict[str, Any]:
        """Get information about the agent."""
        info = {
            "name": "MCTSAgent",
            "type": "mcts",
            "description": "Monte Carlo Tree Search with UCT and heuristic rollouts",
            "parameters": {
                "iterations": self.iterations,
                "time_limit": self.time_limit,
                "exploration_constant": self.exploration_constant,
                "use_transposition_table": self.use_transposition_table,
                "max_rollout_moves": self.max_rollout_moves,
                "learned_model_path": self.learned_model_path,
                "leaf_evaluation_enabled": self.leaf_evaluation_enabled,
                "progressive_bias_enabled": self.progressive_bias_enabled,
                "progressive_bias_weight": self.progressive_bias_weight,
                "potential_shaping_enabled": self.potential_shaping_enabled,
                "potential_shaping_gamma": self.potential_shaping_gamma,
                "potential_shaping_weight": self.potential_shaping_weight,
                "potential_mode": self.potential_mode,
                "progressive_widening_enabled": self.progressive_widening_enabled,
                "pw_c": self.pw_c,
                "pw_alpha": self.pw_alpha,
                "progressive_history_enabled": self.progressive_history_enabled,
                "progressive_history_weight": self.progressive_history_weight,
                "heuristic_move_ordering": self.heuristic_move_ordering,
                # Layer 4
                "rollout_policy": self.rollout_policy,
                "two_ply_top_k": self.two_ply_top_k,
                "rollout_cutoff_depth": self.rollout_cutoff_depth,
                "minimax_backup_alpha": self.minimax_backup_alpha,
                # Layer 5
                "rave_enabled": self.rave_enabled,
                "rave_k": self.rave_k,
                "nst_enabled": self.nst_enabled,
                "nst_weight": self.nst_weight,
                # Layer 8
                "num_workers": self.num_workers,
                "virtual_loss": self.virtual_loss,
                "parallel_strategy": self.parallel_strategy,
                # Layer 9
                "adaptive_exploration_enabled": self.adaptive_exploration_enabled,
                "adaptive_exploration_base": self.adaptive_exploration_base,
                "adaptive_exploration_avg_bf": self.adaptive_exploration_avg_bf,
                "adaptive_rollout_depth_enabled": self.adaptive_rollout_depth_enabled,
                "adaptive_rollout_depth_base": self.adaptive_rollout_depth_base,
                "adaptive_rollout_depth_avg_bf": self.adaptive_rollout_depth_avg_bf,
                "sufficiency_threshold_enabled": self.sufficiency_threshold_enabled,
                "loss_avoidance_enabled": self.loss_avoidance_enabled,
                "loss_avoidance_threshold": self.loss_avoidance_threshold,
            },
            "stats": self.stats.copy()
        }

        if self.transposition_table:
            info["transposition_stats"] = self.transposition_table.get_stats()

        if self._search_trace is not None:
            info["search_trace"] = self._search_trace.to_dict()

        return info

    def reset(self):
        """Reset agent state (per-move stats).

        Note: progressive history table is NOT reset here — it accumulates
        across moves within a game. Call ``reset_history()`` between games.
        """
        self.stats = {
            "iterations_run": 0,
            "time_elapsed": 0.0,
            "transposition_hits": 0,
            "rollout_rewards": [],
            "leaf_eval_calls": 0,
            "progressive_bias_updates": 0,
            "potential_shaping_terms": [],
            "evaluator_errors": 0,
            "pw_expansions_saved": 0,
            "history_table_size": 0,
            # Layer 4
            "two_ply_evals": 0,
            "cutoff_evals": 0,
            "minimax_updates": 0,
            # Layer 8
            "parallel_workers": 0,
            "parallel_strategy": "none",
            "parallel_trees_merged": 0,
            "virtual_loss_applications": 0,
            # Layer 9
            "adaptive_c_value": 0.0,
            "adaptive_rollout_depth": 0,
            "sufficiency_activations": 0,
            "loss_avoidance_triggers": 0,
        }

        if self.transposition_table:
            self.transposition_table.clear()

    def reset_history(self):
        """Reset progressive history and NST tables (call between games).

        RAVE tables are per-node (on the tree) and auto-reset when a new
        tree is constructed each move.
        """
        self._history_table.clear()
        self._nst_table.clear()
        self._last_root_action_key = None

    def set_seed(self, seed: int):
        """Set random seed for reproducible behavior."""
        self.zobrist_hash = ZobristHash(seed=seed)
        self.rollout_agent.set_seed(seed)
        self._rng = np.random.RandomState(seed)

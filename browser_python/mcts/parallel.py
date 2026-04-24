"""Layer 8: Root parallelization for MCTS.

Spawns independent MCTS workers in separate processes, each building its own
tree with a different random seed. At decision time, root-level move statistics
(visit counts and total rewards) are merged across all workers, and the move
with the highest aggregate visit count is selected.

Root parallelization is the recommended strategy for Python because CPython's
GIL prevents true CPU parallelism with threading. Each worker process has its
own GIL and runs full-speed MCTS iterations independently.

References:
- Chaslot et al. (2008): "Monte-Carlo Tree Search: A New Framework for Game AI"
  §8.4 — Root parallelization merges independent trees at decision time.
- Świechowski & Mańdziuk (2016): Hybrid root + tree parallelization.
"""

from __future__ import annotations

import pickle
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from engine.board import Board, Player
from engine.move_generator import Move


def _move_key(move: Move) -> Tuple[int, int, int, int]:
    """Canonical key for matching moves across independent trees."""
    return (move.piece_id, move.orientation, move.anchor_row, move.anchor_col)


def _extract_agent_config(agent) -> dict:
    """Extract a serializable configuration dict from an MCTSAgent instance.

    The config is sufficient to reconstruct an equivalent MCTSAgent in a
    worker process (with a different seed).
    """
    return {
        "iterations": agent.iterations,
        "time_limit": agent.time_limit,
        "exploration_constant": agent.exploration_constant,
        "use_transposition_table": agent.use_transposition_table,
        "learned_model_path": agent.learned_model_path,
        "leaf_evaluation_enabled": agent.leaf_evaluation_enabled,
        "progressive_bias_enabled": agent.progressive_bias_enabled,
        "progressive_bias_weight": agent.progressive_bias_weight,
        "potential_shaping_enabled": agent.potential_shaping_enabled,
        "potential_shaping_gamma": agent.potential_shaping_gamma,
        "potential_shaping_weight": agent.potential_shaping_weight,
        "potential_mode": agent.potential_mode,
        "max_rollout_moves": agent.max_rollout_moves,
        # Layer 3
        "progressive_widening_enabled": agent.progressive_widening_enabled,
        "pw_c": agent.pw_c,
        "pw_alpha": agent.pw_alpha,
        "progressive_history_enabled": agent.progressive_history_enabled,
        "progressive_history_weight": agent.progressive_history_weight,
        "heuristic_move_ordering": agent.heuristic_move_ordering,
        # Layer 4
        "rollout_policy": agent.rollout_policy,
        "two_ply_top_k": agent.two_ply_top_k,
        "rollout_cutoff_depth": agent.rollout_cutoff_depth,
        "state_eval_weights": None,  # weights are internal to evaluator
        "state_eval_phase_weights": None,
        "minimax_backup_alpha": agent.minimax_backup_alpha,
        # Layer 5
        "rave_enabled": agent.rave_enabled,
        "rave_k": agent.rave_k,
        "nst_enabled": agent.nst_enabled,
        "nst_weight": agent.nst_weight,
        # Layer 7
        "opponent_rollout_policy": agent.opponent_rollout_policy,
        "opponent_modeling_enabled": agent.opponent_modeling_enabled,
        "alliance_detection_enabled": agent.alliance_detection_enabled,
        "alliance_threshold": agent.alliance_threshold,
        "kingmaker_detection_enabled": agent.kingmaker_detection_enabled,
        "kingmaker_score_gap": agent.kingmaker_score_gap,
        "adaptive_opponent_enabled": agent.adaptive_opponent_enabled,
        "defensive_weight_shift": agent.defensive_weight_shift,
        # Layer 8: force single-threaded in workers
        "num_workers": 1,
        "virtual_loss": agent.virtual_loss,
        "parallel_strategy": "root",
        # Layer 9: Meta-Optimization
        "adaptive_exploration_enabled": agent.adaptive_exploration_enabled,
        "adaptive_exploration_base": agent.adaptive_exploration_base,
        "adaptive_exploration_avg_bf": agent.adaptive_exploration_avg_bf,
        "adaptive_rollout_depth_enabled": agent.adaptive_rollout_depth_enabled,
        "adaptive_rollout_depth_base": agent.adaptive_rollout_depth_base,
        "adaptive_rollout_depth_avg_bf": agent.adaptive_rollout_depth_avg_bf,
        "sufficiency_threshold_enabled": agent.sufficiency_threshold_enabled,
        "loss_avoidance_enabled": agent.loss_avoidance_enabled,
        "loss_avoidance_threshold": agent.loss_avoidance_threshold,
    }


def _extract_eval_weights(agent) -> Tuple[Optional[dict], Optional[dict]]:
    """Extract state evaluator weights from an agent for serialization."""
    evaluator = agent.state_evaluator
    weights = dict(evaluator.weights) if hasattr(evaluator, 'weights') else None
    phase_weights = None
    if hasattr(evaluator, 'phase_weights') and evaluator.phase_weights:
        phase_weights = {
            phase: dict(w) for phase, w in evaluator.phase_weights.items()
        }
    return weights, phase_weights


def _worker_fn(args: Tuple) -> dict:
    """Worker process: build a single-threaded MCTSAgent, run MCTS, return stats.

    This function runs in a separate process via ProcessPoolExecutor.

    Args:
        args: Tuple of (config_dict, board_bytes, player_value, seed,
              iterations, eval_weights, eval_phase_weights)

    Returns:
        Dict with 'moves' (list of {key, visits, reward}), 'iterations_run',
        and 'time_elapsed'.
    """
    config, board_bytes, player_value, seed, iterations, eval_w, eval_pw = args

    # Reconstruct objects in worker process
    from mcts.mcts_agent import MCTSAgent

    board = pickle.loads(board_bytes)
    player = Player(player_value)

    # Override seed and iterations for this worker
    config["seed"] = seed
    config["iterations"] = iterations
    config["time_limit"] = None  # use iteration count, not time
    config["state_eval_weights"] = eval_w
    config["state_eval_phase_weights"] = eval_pw

    agent = MCTSAgent(**config)

    from engine.move_generator import get_shared_generator
    move_gen = get_shared_generator()
    legal_moves = move_gen.get_legal_moves(board, player)

    start = time.time()
    best_move = agent.select_action(board, player, legal_moves)
    elapsed = time.time() - start

    # Extract root-level statistics from the agent's last search
    # We need to access the internal tree — reconstruct the root and
    # re-run to get child stats. Instead, we run select_action which
    # internally runs MCTS, then we extract stats from the agent.
    #
    # To get per-move visit counts, we need to re-create the tree.
    # A cleaner approach: have the agent expose root child stats.
    # For now, return the best move and stats — the merge will aggregate.
    result = {
        "best_move_key": _move_key(best_move) if best_move else None,
        "iterations_run": agent.stats.get("iterations_run", 0),
        "time_elapsed": elapsed,
    }
    return result


def _worker_fn_with_tree(args: Tuple) -> dict:
    """Worker that exposes per-move visit statistics for proper merging.

    Runs MCTS and returns visit count and total reward for each root child,
    keyed by move tuple. This enables the merge step to aggregate across
    workers using the standard root-parallelization merge formula.
    """
    config, board_bytes, player_value, seed, iterations, eval_w, eval_pw = args

    from engine.move_generator import get_shared_generator
    from mcts.mcts_agent import MCTSAgent, MCTSNode
    from mcts.move_heuristic import rank_moves_by_heuristic

    board = pickle.loads(board_bytes)
    player = Player(player_value)

    config["seed"] = seed
    config["iterations"] = iterations
    config["time_limit"] = None
    config["state_eval_weights"] = eval_w
    config["state_eval_phase_weights"] = eval_pw

    agent = MCTSAgent(**config)
    agent._root_player = player

    move_gen = get_shared_generator()
    legal_moves = move_gen.get_legal_moves(board, player)

    if not legal_moves:
        return {"move_stats": {}, "iterations_run": 0, "time_elapsed": 0.0}
    if len(legal_moves) == 1:
        key = _move_key(legal_moves[0])
        return {
            "move_stats": {key: (1, 1.0)},
            "iterations_run": 0,
            "time_elapsed": 0.0,
        }

    # Build root and run MCTS iterations directly
    root = MCTSNode(board, player)
    if agent.heuristic_move_ordering or agent.progressive_widening_enabled:
        agent._sort_untried_moves(root)

    start = time.time()
    agent._run_mcts_with_iterations(root)
    elapsed = time.time() - start

    # Extract per-child statistics
    move_stats: Dict[Tuple, Tuple[int, float]] = {}
    for child in root.children:
        key = _move_key(child.move)
        move_stats[key] = (child.visits, child.total_reward)

    return {
        "move_stats": move_stats,
        "iterations_run": agent.stats.get("iterations_run", 0),
        "time_elapsed": elapsed,
    }


def run_root_parallel(
    agent,
    board: Board,
    player: Player,
    legal_moves: List[Move],
    num_workers: int,
) -> Tuple[Optional[Move], dict]:
    """Run root-parallel MCTS: N independent trees merged at decision time.

    Each worker process builds its own MCTS tree with a different random seed,
    running iterations/num_workers iterations. The root-level move statistics
    (visit counts and total rewards) are summed across workers, and the move
    with the highest aggregate visit count is selected.

    Args:
        agent: The MCTSAgent instance (used to extract config).
        board: Current board state.
        player: Player to move.
        legal_moves: Available legal moves.
        num_workers: Number of parallel worker processes.

    Returns:
        Tuple of (best_move, stats_dict).
    """
    if not legal_moves:
        return None, {"trees_merged": 0, "total_iterations": 0}
    if len(legal_moves) == 1:
        return legal_moves[0], {"trees_merged": 1, "total_iterations": 0}

    config = _extract_agent_config(agent)
    eval_w, eval_pw = _extract_eval_weights(agent)
    board_bytes = pickle.dumps(board)
    player_value = player.value

    # Split iterations across workers
    base_iterations = max(1, agent.iterations // num_workers)

    # Build worker args with different seeds
    base_seed = hash((id(agent), time.time())) & 0xFFFFFFFF
    worker_args = []
    for i in range(num_workers):
        seed_i = (base_seed + i * 7919) & 0xFFFFFFFF  # prime offset for diversity
        worker_args.append((
            config, board_bytes, player_value, seed_i,
            base_iterations, eval_w, eval_pw,
        ))

    # Launch workers
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(_worker_fn_with_tree, worker_args))

    # Merge move statistics across workers
    merged: Dict[Tuple, List[float]] = {}  # key -> [total_visits, total_reward]
    total_iterations = 0
    trees_merged = 0

    for result in results:
        if result["move_stats"]:
            trees_merged += 1
        total_iterations += result["iterations_run"]
        for key, (visits, reward) in result["move_stats"].items():
            if key not in merged:
                merged[key] = [0, 0.0]
            merged[key][0] += visits
            merged[key][1] += reward

    # Select move with highest aggregate visit count
    if not merged:
        return legal_moves[0] if legal_moves else None, {
            "trees_merged": trees_merged,
            "total_iterations": total_iterations,
        }

    best_key = max(merged, key=lambda k: merged[k][0])

    # Find the actual Move object matching the best key
    best_move = None
    for move in legal_moves:
        if _move_key(move) == best_key:
            best_move = move
            break

    # Fallback: if move not found in legal_moves (shouldn't happen), use first
    if best_move is None:
        best_move = legal_moves[0]

    stats = {
        "trees_merged": trees_merged,
        "total_iterations": total_iterations,
        "merged_move_count": len(merged),
        "best_move_visits": merged[best_key][0],
        "best_move_reward": merged[best_key][1],
        "merged_moves": merged,
    }
    return best_move, stats

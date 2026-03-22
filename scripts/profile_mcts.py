#!/usr/bin/env python3
"""Structured MCTS profiler: per-phase timing breakdown.

Instruments MCTSAgent to measure time spent in:
    - Selection (tree traversal)
    - Expansion (node creation + board copy + move gen)
    - Simulation (rollout or leaf evaluation)
    - Backpropagation
    - Board.copy() in isolation
    - Memory footprint per MCTSNode

Usage:
    python scripts/profile_mcts.py [--iterations 500] [--game-phase early|mid|late|all]
    python scripts/profile_mcts.py --output profile_report.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.board import Board, Player
from engine.move_generator import LegalMoveGenerator, get_shared_generator
from mcts.mcts_agent import MCTSAgent, MCTSNode
from tests.utils_game_states import generate_random_valid_state


def measure_board_copy(board: Board, n_trials: int = 1000) -> dict:
    """Measure Board.copy() cost."""
    times = []
    for _ in range(n_trials):
        start = time.perf_counter()
        _ = board.copy()
        times.append(time.perf_counter() - start)
    times_ms = [t * 1000 for t in times]
    return {
        "mean_us": sum(times_ms) / len(times_ms) * 1000,
        "min_us": min(times_ms) * 1000,
        "max_us": max(times_ms) * 1000,
        "n_trials": n_trials,
    }


def measure_node_memory(board: Board, player: Player) -> dict:
    """Estimate memory footprint of a single MCTSNode."""
    import sys as _sys

    node = MCTSNode(board, player)
    # Shallow size of node object
    node_shallow = _sys.getsizeof(node)
    # Size of key attributes
    children_size = _sys.getsizeof(node.children)
    untried_size = _sys.getsizeof(node.untried_moves)
    # Estimate: board copy is the big one
    board_grid_size = node.board.grid.nbytes
    board_obj_size = _sys.getsizeof(node.board)

    return {
        "node_shallow_bytes": node_shallow,
        "children_list_bytes": children_size,
        "untried_moves_list_bytes": untried_size,
        "board_grid_bytes": board_grid_size,
        "board_object_bytes": board_obj_size,
        "estimated_total_bytes": node_shallow + board_grid_size + untried_size + children_size,
        "n_untried_moves": len(node.untried_moves),
    }


def profile_mcts_phases(
    board: Board,
    player: Player,
    iterations: int,
    exploration_constant: float = 1.414,
) -> dict:
    """Profile MCTS iteration phases with timing instrumentation.

    Runs MCTS from scratch on the given board state and measures
    time spent in each phase of each iteration.
    """
    move_generator = get_shared_generator()
    legal_moves = move_generator.get_legal_moves(board, player)

    if not legal_moves or len(legal_moves) == 1:
        return {"error": "Not enough legal moves to profile", "n_legal_moves": len(legal_moves)}

    # Create a patched MCTSAgent to instrument timing
    agent = MCTSAgent(
        iterations=iterations,
        exploration_constant=exploration_constant,
        use_transposition_table=True,
    )

    # Timing accumulators
    t_selection = 0.0
    t_expansion = 0.0
    t_simulation = 0.0
    t_backprop = 0.0
    n_iterations = 0

    # Run instrumented MCTS
    root = MCTSNode(board, player)
    overall_start = time.perf_counter()

    for _ in range(iterations):
        # Selection
        t0 = time.perf_counter()
        node = agent._selection(root)
        t1 = time.perf_counter()
        t_selection += t1 - t0

        # Expansion
        t0 = time.perf_counter()
        if not node.is_fully_expanded() and not node.is_terminal():
            parent = node
            node = node.expand()
            if node is None:
                t_expansion += time.perf_counter() - t0
                continue
            agent._update_progressive_bias(parent, node)
        t1 = time.perf_counter()
        t_expansion += t1 - t0

        # Simulation
        t0 = time.perf_counter()
        reward = agent._simulation(node)
        t1 = time.perf_counter()
        t_simulation += t1 - t0

        # Backpropagation
        t0 = time.perf_counter()
        agent._backpropagation(node, reward)
        t1 = time.perf_counter()
        t_backprop += t1 - t0

        n_iterations += 1

    overall_elapsed = time.perf_counter() - overall_start

    # Collect tree diagnostics
    agent._collect_tree_diagnostics(root)

    total_phase_time = t_selection + t_expansion + t_simulation + t_backprop
    overhead = overall_elapsed - total_phase_time

    def pct(t):
        return round(100 * t / overall_elapsed, 1) if overall_elapsed > 0 else 0

    return {
        "iterations": n_iterations,
        "total_time_s": round(overall_elapsed, 4),
        "iterations_per_sec": round(n_iterations / overall_elapsed, 1) if overall_elapsed > 0 else 0,
        "n_legal_moves": len(legal_moves),
        "phases": {
            "selection": {
                "total_s": round(t_selection, 4),
                "pct": pct(t_selection),
                "per_iter_us": round(t_selection / n_iterations * 1e6, 1) if n_iterations > 0 else 0,
            },
            "expansion": {
                "total_s": round(t_expansion, 4),
                "pct": pct(t_expansion),
                "per_iter_us": round(t_expansion / n_iterations * 1e6, 1) if n_iterations > 0 else 0,
            },
            "simulation": {
                "total_s": round(t_simulation, 4),
                "pct": pct(t_simulation),
                "per_iter_us": round(t_simulation / n_iterations * 1e6, 1) if n_iterations > 0 else 0,
            },
            "backpropagation": {
                "total_s": round(t_backprop, 4),
                "pct": pct(t_backprop),
                "per_iter_us": round(t_backprop / n_iterations * 1e6, 1) if n_iterations > 0 else 0,
            },
            "overhead": {
                "total_s": round(overhead, 4),
                "pct": pct(overhead),
            },
        },
        "tree_stats": {
            "tree_size": agent.stats.get("tree_size"),
            "tree_depth_max": agent.stats.get("tree_depth_max"),
            "tree_depth_mean": round(agent.stats.get("tree_depth_mean", 0), 2),
            "visit_entropy": round(agent.stats.get("visit_entropy", 0), 4),
            "branching_factor": agent.stats.get("branching_factor"),
        },
    }


def profile_move_generation(board: Board, player: Player, n_trials: int = 100) -> dict:
    """Profile move generation cost."""
    move_gen = LegalMoveGenerator()
    times = []
    n_moves = 0
    for _ in range(n_trials):
        start = time.perf_counter()
        moves = move_gen.get_legal_moves(board, player)
        times.append(time.perf_counter() - start)
        n_moves = len(moves)
    times_ms = [t * 1000 for t in times]
    return {
        "mean_ms": round(sum(times_ms) / len(times_ms), 3),
        "min_ms": round(min(times_ms), 3),
        "max_ms": round(max(times_ms), 3),
        "n_moves": n_moves,
        "n_trials": n_trials,
    }


GAME_PHASES = {
    "early": 8,
    "mid": 25,
    "late": 45,
}


def run_full_profile(iterations: int, game_phase: str, seed: int = 42) -> dict:
    """Run full profiler for a given game phase."""
    n_moves = GAME_PHASES[game_phase]
    board, player = generate_random_valid_state(n_moves, seed=seed)

    results = {
        "game_phase": game_phase,
        "board_moves_played": n_moves,
        "player": player.name,
        "mcts_profile": profile_mcts_phases(board, player, iterations),
        "move_generation": profile_move_generation(board, player),
        "board_copy": measure_board_copy(board),
        "node_memory": measure_node_memory(board, player),
    }
    return results


def print_report(results: dict) -> None:
    """Print human-readable profiler report."""
    print("=" * 70)
    print(f"MCTS Profiler Report — {results['game_phase']} game ({results['board_moves_played']} moves played)")
    print("=" * 70)
    print()

    mcts = results["mcts_profile"]
    if "error" in mcts:
        print(f"  ERROR: {mcts['error']}")
        return

    print(f"  Iterations: {mcts['iterations']}")
    print(f"  Total time: {mcts['total_time_s']}s ({mcts['iterations_per_sec']} iter/s)")
    print(f"  Legal moves at root: {mcts['n_legal_moves']}")
    print()

    print("  Phase Breakdown:")
    print(f"  {'Phase':<20} {'Time (s)':<12} {'%':<8} {'Per-iter (us)':<15}")
    print(f"  {'-'*55}")
    for phase_name, phase_data in mcts["phases"].items():
        t = phase_data.get("total_s", 0)
        p = phase_data.get("pct", 0)
        per = phase_data.get("per_iter_us", "—")
        print(f"  {phase_name:<20} {t:<12} {p:<8} {per}")
    print()

    ts = mcts["tree_stats"]
    print("  Tree Stats:")
    print(f"    Size: {ts['tree_size']} nodes")
    print(f"    Max depth: {ts['tree_depth_max']}")
    print(f"    Mean depth: {ts['tree_depth_mean']}")
    print(f"    Visit entropy: {ts['visit_entropy']}")
    print(f"    Branching factor: {ts['branching_factor']}")
    print()

    mg = results["move_generation"]
    print(f"  Move Generation: {mg['mean_ms']:.3f}ms avg ({mg['n_moves']} moves, {mg['n_trials']} trials)")
    print()

    bc = results["board_copy"]
    print(f"  Board.copy(): {bc['mean_us']:.1f}us avg ({bc['n_trials']} trials)")
    print()

    nm = results["node_memory"]
    print(f"  MCTSNode Memory:")
    print(f"    Node object: {nm['node_shallow_bytes']} bytes")
    print(f"    Board grid: {nm['board_grid_bytes']} bytes")
    print(f"    Estimated total: {nm['estimated_total_bytes']} bytes")
    print(f"    Untried moves: {nm['n_untried_moves']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="MCTS Profiler")
    parser.add_argument("--iterations", type=int, default=500, help="MCTS iterations per profile")
    parser.add_argument("--game-phase", choices=["early", "mid", "late", "all"], default="all",
                        help="Game phase to profile")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    phases = list(GAME_PHASES.keys()) if args.game_phase == "all" else [args.game_phase]

    all_results = {}
    for phase in phases:
        print(f"\nProfiling {phase} game...")
        results = run_full_profile(args.iterations, phase, seed=args.seed)
        all_results[phase] = results
        print_report(results)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nJSON report written to: {output_path}")


if __name__ == "__main__":
    main()

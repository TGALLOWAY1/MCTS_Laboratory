#!/usr/bin/env python3
"""Calibrate MCTS throughput at different rollout cutoff depths.

Measures actual iterations/second for each cutoff depth at each game phase,
producing calibration data for Layer 10 fixed-compute experiments.

Usage:
    python scripts/calibrate_throughput.py
    python scripts/calibrate_throughput.py --iterations 300 --output data/throughput_calibration.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.board import Board, Player
from engine.move_generator import LegalMoveGenerator, get_shared_generator
from mcts.mcts_agent import MCTSAgent
from tests.utils_game_states import generate_random_valid_state

GAME_PHASES = {
    "early": 8,
    "mid": 28,
    "late": 48,
}

CUTOFF_DEPTHS = [0, 5, 10, 15]  # Skip full rollout and depth 20 (infeasible)


def measure_throughput(
    board: Board,
    player: Player,
    cutoff_depth,
    iterations: int = 200,
) -> dict:
    """Measure MCTS iterations/sec at a given cutoff depth."""
    params = {
        "exploration_constant": 1.414,
        "max_rollout_moves": 50,
    }
    if cutoff_depth is not None:
        params["rollout_cutoff_depth"] = cutoff_depth

    agent = MCTSAgent(**params)
    move_gen = get_shared_generator()
    legal_moves = move_gen.get_legal_moves(board, player)

    if not legal_moves:
        return {"error": "no legal moves", "iterations_per_sec": 0}

    # Run MCTS with fixed iteration count
    agent.iterations = iterations
    agent.time_limit = None

    start = time.perf_counter()
    action = agent.select_action(board, player, legal_moves)
    elapsed = time.perf_counter() - start

    actual_iters = agent.stats.get("iterations_run", iterations)
    iters_per_sec = actual_iters / elapsed if elapsed > 0 else 0
    iters_per_ms = iters_per_sec / 1000.0

    return {
        "cutoff_depth": cutoff_depth if cutoff_depth is not None else "full",
        "iterations_requested": iterations,
        "iterations_run": actual_iters,
        "elapsed_sec": round(elapsed, 3),
        "iterations_per_sec": round(iters_per_sec, 1),
        "iterations_per_ms": round(iters_per_ms, 3),
        "legal_moves": len(legal_moves),
    }


def main():
    parser = argparse.ArgumentParser(description="Calibrate MCTS throughput")
    parser.add_argument(
        "--iterations", type=int, default=200, help="Iterations per measurement"
    )
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    results = {}
    print(f"{'Phase':<8} {'Depth':<8} {'Iters':<8} {'Time(s)':<10} {'Iter/s':<10} {'Iter/ms':<10} {'Moves':<6}")
    print("-" * 70)

    for phase_name, n_moves in GAME_PHASES.items():
        board, player = generate_random_valid_state(n_moves, seed=args.seed)
        results[phase_name] = {}
        print(f"\n--- {phase_name} game ({n_moves} moves played) ---")

        for depth in CUTOFF_DEPTHS:
            depth_label = str(depth) if depth is not None else "full"
            # Use fewer iterations for deep rollouts to keep calibration fast
            iters = args.iterations if depth is None or depth <= 5 else max(10, args.iterations // 10)
            r = measure_throughput(board, player, depth, iters)
            results[phase_name][depth_label] = r

            if "error" not in r:
                print(
                    f"{phase_name:<8} {depth_label:<8} {r['iterations_run']:<8} "
                    f"{r['elapsed_sec']:<10} {r['iterations_per_sec']:<10} "
                    f"{r['iterations_per_ms']:<10} {r['legal_moves']:<6}"
                )
            else:
                print(f"{phase_name:<8} {depth_label:<8} ERROR: {r['error']}")

    # Summary: recommended iterations_per_ms for each depth
    print("\n" + "=" * 70)
    print("Recommended iterations_per_ms values (averaged across phases):")
    print("=" * 70)
    for depth in CUTOFF_DEPTHS:
        depth_label = str(depth) if depth is not None else "full"
        values = []
        for phase_name in GAME_PHASES:
            r = results[phase_name].get(depth_label, {})
            if "iterations_per_ms" in r and r["iterations_per_ms"] > 0:
                values.append(r["iterations_per_ms"])
        if values:
            avg = sum(values) / len(values)
            print(f"  depth={depth_label:>5}: {avg:.3f} iter/ms (range: {min(values):.3f} - {max(values):.3f})")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(results, f, indent=2)
        print(f"\nJSON written to: {output_path}")


if __name__ == "__main__":
    main()

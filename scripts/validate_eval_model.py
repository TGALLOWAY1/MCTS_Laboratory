#!/usr/bin/env python
"""Validate a trained win-probability model by running head-to-head arena games.

1. Inference speed check — verifies ``predict_player_win_probability`` < 5 ms.
2. Head-to-head arena — compares base (pure rollout), leaf_eval only, and
   leaf_eval + progressive_bias configurations.
3. Reports win rates across configurations.

Example
-------
python scripts/validate_eval_model.py \
    --model models/eval_v1.pkl \
    --num-games 100 \
    --thinking-time-ms 100
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from analytics.tournament.arena_runner import (
    AgentConfig,
    RunConfig,
    SnapshotConfig,
    _prepare_run_directory,
    game_seed_from_run_seed,
    run_single_game,
)
from analytics.tournament.scheduler import generate_matchups, validate_balance
from analytics.tournament.tuning import (
    MctsTuning,
    TuningSet,
    _BASE_PARAMS,
)
from engine.board import Board, Player
from engine.move_generator import get_shared_generator
from mcts.learned_evaluator import LearnedWinProbabilityEvaluator


# ---------------------------------------------------------------------------
# Inference Speed Benchmark
# ---------------------------------------------------------------------------

def benchmark_inference(model_path: str, num_calls: int = 50) -> float:
    """Return median inference time in ms for predict_player_win_probability."""
    evaluator = LearnedWinProbabilityEvaluator(model_path)
    board = Board()
    move_gen = get_shared_generator()

    # Advance board a few moves so features are non-trivial
    from engine.game import BlokusGame

    game = BlokusGame(enable_telemetry=False)
    for _ in range(4):
        player = game.board.current_player
        legal = move_gen.get_legal_moves(game.board, player)
        if legal:
            game.make_move(legal[0], player)
        else:
            game.board._update_current_player()
    board = game.board

    # Warm-up
    for _ in range(3):
        evaluator.predict_player_win_probability(board, Player.RED)

    # Timed calls
    times_ms: list[float] = []
    for _ in range(num_calls):
        t0 = time.perf_counter()
        evaluator.predict_player_win_probability(board, Player.RED)
        t1 = time.perf_counter()
        times_ms.append((t1 - t0) * 1000)

    median = float(np.median(times_ms))
    p95 = float(np.percentile(times_ms, 95))
    print(f"  Inference speed ({num_calls} calls):")
    print(f"    Median: {median:.2f} ms")
    print(f"    P95:    {p95:.2f} ms")
    print(f"    Max:    {max(times_ms):.2f} ms")

    if median > 5.0:
        print(f"  WARNING: Median inference {median:.2f}ms exceeds 5ms budget!")
    else:
        print(f"  OK: Median inference within 5ms budget.")
    return median


# ---------------------------------------------------------------------------
# Head-to-head arena
# ---------------------------------------------------------------------------

def run_validation_arena(
    model_path: str,
    num_games: int,
    thinking_time_ms: int,
    seed: int,
    agent_backend: str,
    output_root: str,
) -> Dict[str, Any]:
    """Run a small arena comparing base vs leaf_eval vs leaf_eval+bias."""

    tunings = [
        MctsTuning("base_rollout", {**_BASE_PARAMS}),
        MctsTuning("leaf_eval_only", {
            **_BASE_PARAMS,
            "leaf_evaluation_enabled": True,
            "progressive_bias_enabled": False,
            "learned_model_path": model_path,
        }),
        MctsTuning("leaf_eval_bias_0.25", {
            **_BASE_PARAMS,
            "leaf_evaluation_enabled": True,
            "progressive_bias_enabled": True,
            "progressive_bias_weight": 0.25,
            "learned_model_path": model_path,
        }),
        MctsTuning("leaf_eval_bias_shaping", {
            **_BASE_PARAMS,
            "leaf_evaluation_enabled": True,
            "progressive_bias_enabled": True,
            "progressive_bias_weight": 0.25,
            "potential_shaping_enabled": True,
            "potential_shaping_weight": 1.0,
            "learned_model_path": model_path,
        }),
    ]

    tuning_names = [t.name for t in tunings]

    # Build agent configs
    agent_configs: Dict[str, AgentConfig] = {}
    for tuning in tunings:
        agent_configs[tuning.name] = AgentConfig(
            name=tuning.name,
            type=agent_backend,
            thinking_time_ms=thinking_time_ms,
            params=tuning.resolve_params(thinking_time_ms),
        )

    # Generate matchups
    matchups = generate_matchups(tuning_names, num_games, seed, "randomized")
    validate_balance(matchups, tuning_names)

    # Build RunConfig (needed by run_single_game)
    pseudo_agents = list(agent_configs.values())[:4]
    run_config = RunConfig(
        agents=pseudo_agents,
        num_games=num_games,
        seed=seed,
        seat_policy="randomized",
        output_root=output_root,
        max_turns=2500,
        notes="eval model validation",
        snapshots=SnapshotConfig(enabled=False),
    )

    run_id, run_dir = _prepare_run_directory(run_config)

    # Track results
    results_by_agent: Dict[str, Dict[str, Any]] = {
        name: {"wins": 0, "scores": [], "games": 0} for name in tuning_names
    }

    print(f"\n  Running {num_games} arena games ({agent_backend}, {thinking_time_ms}ms)...")
    t0 = time.time()

    for gi, matchup in enumerate(matchups):
        # Build seat assignment: "seat_index+1" -> agent_name (string keys)
        seat_assignment = {
            str(seat + 1): agent_name
            for seat, agent_name in matchup.seats.items()
        }

        game_seed = game_seed_from_run_seed(seed, matchup.game_index)

        record, _ = run_single_game(
            run_id=run_id,
            game_index=matchup.game_index,
            game_seed=game_seed,
            run_config=run_config,
            seat_assignment=seat_assignment,
            agent_configs=agent_configs,
        )

        # Parse results from game record
        agent_scores = record.get("agent_scores", {})
        winner_agents = record.get("winner_agents", [])

        for agent_name in set(seat_assignment.values()):
            score = agent_scores.get(agent_name, 0)
            results_by_agent[agent_name]["scores"].append(score)
            results_by_agent[agent_name]["games"] += 1

        # Credit wins
        if len(winner_agents) == 1:
            results_by_agent[winner_agents[0]]["wins"] += 1

        if (gi + 1) % max(1, num_games // 10) == 0:
            elapsed = time.time() - t0
            print(f"    [{gi + 1}/{num_games}] ({elapsed:.1f}s)")

    elapsed = time.time() - t0

    # Report
    print(f"\n=== Validation Results ({elapsed:.1f}s) ===")
    print(f"{'Agent':<30} {'Win%':>8} {'Wins':>6} {'Games':>6} {'Avg Score':>10}")
    print("-" * 64)

    for name in tuning_names:
        info = results_by_agent[name]
        games = info["games"]
        win_pct = (info["wins"] / games * 100) if games else 0
        avg_score = float(np.mean(info["scores"])) if info["scores"] else 0
        print(f"{name:<30} {win_pct:>7.1f}% {info['wins']:>6} {games:>6} {avg_score:>10.1f}")

    return results_by_agent


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate trained eval model.")
    parser.add_argument("--model", type=str, required=True, help="Path to .pkl model artifact.")
    parser.add_argument("--num-games", type=int, default=100, help="Arena games to play.")
    parser.add_argument("--thinking-time-ms", type=int, default=100, help="Time budget per move.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--agent-backend",
        type=str,
        choices=["mcts", "fast_mcts"],
        default="mcts",
        help="Base MCTS implementation.",
    )
    parser.add_argument("--output-root", type=str, default="validation_runs", help="Output directory.")
    parser.add_argument("--skip-inference-check", action="store_true", help="Skip inference speed test.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"=== Model Validation ===")
    print(f"  model:            {args.model}")
    print(f"  num_games:        {args.num_games}")
    print(f"  thinking_time_ms: {args.thinking_time_ms}")
    print(f"  agent_backend:    {args.agent_backend}")
    print()

    # Verify model exists
    if not Path(args.model).exists():
        print(f"ERROR: Model file not found: {args.model}")
        return

    # 1. Inference speed check
    if not args.skip_inference_check:
        print("--- Inference Speed Check ---")
        benchmark_inference(args.model)
        print()

    # 2. Head-to-head arena
    print("--- Head-to-Head Arena ---")
    results = run_validation_arena(
        model_path=args.model,
        num_games=args.num_games,
        thinking_time_ms=args.thinking_time_ms,
        seed=args.seed,
        agent_backend=args.agent_backend,
        output_root=args.output_root,
    )

    # Save results
    output_dir = Path(args.output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "validation_results.json"

    serializable = {}
    for name, info in results.items():
        serializable[name] = {
            "wins": info["wins"],
            "games": info["games"],
            "avg_score": float(np.mean(info["scores"])) if info["scores"] else 0,
            "win_rate": info["wins"] / info["games"] if info["games"] else 0,
        }

    with open(results_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"\n  Results saved to: {results_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Layer 3: Action Reduction — Validation & Heuristic Calibration.

Runs validation suite for progressive widening and progressive history:
1. Head-to-head arena: baseline vs PW vs PH vs PW+PH
2. Heuristic calibration: agreement rate between heuristic and MCTS selection
3. Generates a Layer 3 report

Example
-------
python scripts/run_layer3_validation.py \
    --num-games 40 \
    --thinking-time-ms 200 \
    --tuning-set action_reduction_ablation \
    --seed 42
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    get_tuning_set,
    register_tuning_set,
)


# ---------------------------------------------------------------------------
# Heuristic calibration game
# ---------------------------------------------------------------------------

def run_calibration_game(
    thinking_time_ms: int,
    seed: int,
    pw_c: float = 2.0,
    pw_alpha: float = 0.5,
    ph_weight: float = 1.0,
) -> Dict[str, Any]:
    """Play a single game and record heuristic-vs-MCTS agreement per move.

    Returns a dict with per-move diagnostics including:
    - heuristic_rank_of_selected: where the MCTS-selected move ranked in heuristic ordering
    - turn_number: game turn
    - legal_move_count: branching factor at that turn
    """
    from engine.board import Board, Player, _PLAYERS
    from engine.game import BlokusGame
    from engine.move_generator import get_shared_generator
    from mcts.mcts_agent import MCTSAgent
    from mcts.move_heuristic import compute_move_heuristic

    mg = get_shared_generator()
    game = BlokusGame(enable_telemetry=False)

    agent = MCTSAgent(
        time_limit=thinking_time_ms / 1000.0,
        seed=seed,
        progressive_widening_enabled=True,
        pw_c=pw_c,
        pw_alpha=pw_alpha,
        progressive_history_enabled=True,
        progressive_history_weight=ph_weight,
        heuristic_move_ordering=True,
    )

    records = []
    turn = 0

    while not game.board.is_game_over() and turn < 200:
        player = game.board.current_player
        legal = mg.get_legal_moves(game.board, player)
        if not legal:
            game.board._update_current_player()
            turn += 1
            continue

        # Score all moves by heuristic
        scored = [
            (compute_move_heuristic(game.board, player, m, mg), m)
            for m in legal
        ]
        scored.sort(key=lambda x: x[0], reverse=True)  # best first
        heuristic_best_move = scored[0][1]

        # MCTS selection
        agent.reset()
        selected_move = agent.select_action(game.board, player, legal)

        if selected_move is None:
            game.board._update_current_player()
            turn += 1
            continue

        # Find rank of selected move in heuristic ordering
        heuristic_rank = None
        for rank, (_, m) in enumerate(scored):
            if (m.piece_id == selected_move.piece_id
                    and m.orientation == selected_move.orientation
                    and m.anchor_row == selected_move.anchor_row
                    and m.anchor_col == selected_move.anchor_col):
                heuristic_rank = rank
                break

        agreed = (heuristic_rank == 0) if heuristic_rank is not None else False

        info = agent.get_action_info()
        records.append({
            "turn": turn,
            "player": int(player.value),
            "legal_move_count": len(legal),
            "heuristic_rank_of_selected": heuristic_rank,
            "agreed": agreed,
            "selected_piece_id": selected_move.piece_id,
            "heuristic_best_piece_id": heuristic_best_move.piece_id,
            "iterations": info["stats"].get("iterations_run", 0),
            "tree_size": info["stats"].get("tree_size", 0),
            "pw_expansions_saved": info["stats"].get("pw_expansions_saved", 0),
        })

        # Make the selected move
        game.make_move(selected_move, player)
        turn += 1

    # Compute agreement statistics
    agreements = [r["agreed"] for r in records]
    agreement_rate = sum(agreements) / len(agreements) if agreements else 0

    # Phase breakdown
    phase_stats = {"early": [], "mid": [], "late": []}
    for r in records:
        t = r["turn"]
        if t < 20:
            phase_stats["early"].append(r["agreed"])
        elif t < 50:
            phase_stats["mid"].append(r["agreed"])
        else:
            phase_stats["late"].append(r["agreed"])

    phase_agreement = {}
    for phase, vals in phase_stats.items():
        phase_agreement[phase] = sum(vals) / len(vals) if vals else 0

    return {
        "records": records,
        "agreement_rate": agreement_rate,
        "phase_agreement": phase_agreement,
        "total_moves": len(records),
    }


# ---------------------------------------------------------------------------
# Arena validation (reuses the tuning system)
# ---------------------------------------------------------------------------

def run_arena(
    tuning_set_name: str,
    num_games: int,
    thinking_time_ms: int,
    seed: int,
    output_root: str,
) -> Dict[str, Any]:
    """Run an arena tournament with a given tuning set."""
    ts = get_tuning_set(tuning_set_name)
    tuning_names = [t.name for t in ts.tunings]

    agent_configs: Dict[str, AgentConfig] = {}
    for tuning in ts.tunings:
        agent_configs[tuning.name] = AgentConfig(
            name=tuning.name,
            type="mcts",
            thinking_time_ms=thinking_time_ms,
            params=tuning.resolve_params(thinking_time_ms),
        )

    matchups = generate_matchups(tuning_names, num_games, seed, "randomized")
    validate_balance(matchups, tuning_names)

    pseudo_agents = list(agent_configs.values())[:4]
    run_config = RunConfig(
        agents=pseudo_agents,
        num_games=num_games,
        seed=seed,
        seat_policy="randomized",
        output_root=output_root,
        max_turns=2500,
        notes=f"layer3 {tuning_set_name}",
        snapshots=SnapshotConfig(enabled=False),
    )

    run_id, run_dir = _prepare_run_directory(run_config)

    results_by_agent: Dict[str, Dict[str, Any]] = {
        name: {"wins": 0, "scores": [], "games": 0} for name in tuning_names
    }

    print(f"\n  Running {num_games} games: {tuning_set_name} @ {thinking_time_ms}ms...")
    t0 = time.time()

    for gi, matchup in enumerate(matchups):
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

        agent_scores = record.get("agent_scores", {})
        winner_agents = record.get("winner_agents", [])

        for agent_name in set(seat_assignment.values()):
            score = agent_scores.get(agent_name, 0)
            results_by_agent[agent_name]["scores"].append(score)
            results_by_agent[agent_name]["games"] += 1

        if len(winner_agents) == 1:
            results_by_agent[winner_agents[0]]["wins"] += 1

        if (gi + 1) % max(1, num_games // 5) == 0:
            elapsed = time.time() - t0
            print(f"    [{gi + 1}/{num_games}] ({elapsed:.1f}s)")

    elapsed = time.time() - t0

    for name in tuning_names:
        info = results_by_agent[name]
        games = info["games"]
        info["win_rate"] = info["wins"] / games if games else 0
        info["avg_score"] = float(np.mean(info["scores"])) if info["scores"] else 0
        info["score_std"] = float(np.std(info["scores"])) if info["scores"] else 0

    return {
        "tuning_set": tuning_set_name,
        "thinking_time_ms": thinking_time_ms,
        "num_games": num_games,
        "duration_sec": elapsed,
        "agent_results": results_by_agent,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Layer 3: Action Reduction Validation")
    parser.add_argument("--num-games", type=int, default=40)
    parser.add_argument("--thinking-time-ms", type=int, default=200)
    parser.add_argument("--tuning-set", type=str, default="action_reduction_ablation")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-root", type=str, default="validation_runs/layer3")
    parser.add_argument("--skip-arena", action="store_true")
    parser.add_argument("--skip-calibration", action="store_true")
    parser.add_argument("--calibration-games", type=int, default=3,
                        help="Number of games for heuristic calibration analysis")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("Layer 3: Action Reduction Validation")
    print("=" * 60)
    print(f"  tuning_set: {args.tuning_set}")
    print(f"  games:      {args.num_games}")
    print(f"  budget:     {args.thinking_time_ms}ms")
    print()

    results = {}

    # ---- Phase 1: Arena ----
    if not args.skip_arena:
        print("--- Phase 1: Arena Tournament ---")
        arena = run_arena(
            tuning_set_name=args.tuning_set,
            num_games=args.num_games,
            thinking_time_ms=args.thinking_time_ms,
            seed=args.seed,
            output_root=args.output_root,
        )
        results["arena"] = arena

        print(f"\n  Results ({arena['duration_sec']:.0f}s):")
        print(f"  {'Agent':<30} {'Win%':>8} {'Wins':>6} {'Games':>6} {'Avg':>8} {'Std':>6}")
        print("  " + "-" * 64)
        for name in sorted(arena["agent_results"].keys()):
            info = arena["agent_results"][name]
            games = info.get("games", 0)
            wins = info.get("wins", 0)
            pct = wins / games * 100 if games else 0
            avg = info.get("avg_score", 0)
            std = info.get("score_std", 0)
            print(f"  {name:<30} {pct:>7.1f}% {wins:>6} {games:>6} {avg:>8.1f} {std:>5.1f}")
        print()

    # ---- Phase 2: Heuristic Calibration ----
    if not args.skip_calibration:
        print("--- Phase 2: Heuristic Calibration ---")
        all_calibration = []
        for g in range(args.calibration_games):
            print(f"  Calibration game {g + 1}/{args.calibration_games}...", end=" ", flush=True)
            cal = run_calibration_game(
                thinking_time_ms=args.thinking_time_ms,
                seed=args.seed + g,
            )
            all_calibration.append(cal)
            print(f"agreement={cal['agreement_rate']:.1%} ({cal['total_moves']} moves)")

        # Aggregate
        all_records = [r for cal in all_calibration for r in cal["records"]]
        total_agreed = sum(r["agreed"] for r in all_records)
        overall_rate = total_agreed / len(all_records) if all_records else 0

        # Phase breakdown (aggregate)
        phase_agreed = {"early": [], "mid": [], "late": []}
        for r in all_records:
            t = r["turn"]
            if t < 20:
                phase_agreed["early"].append(r["agreed"])
            elif t < 50:
                phase_agreed["mid"].append(r["agreed"])
            else:
                phase_agreed["late"].append(r["agreed"])

        phase_rates = {
            p: sum(vals) / len(vals) if vals else 0
            for p, vals in phase_agreed.items()
        }

        results["calibration"] = {
            "overall_agreement_rate": overall_rate,
            "phase_agreement_rates": phase_rates,
            "total_moves_analysed": len(all_records),
            "games": args.calibration_games,
        }

        print(f"\n  Overall agreement rate: {overall_rate:.1%}")
        for phase in ["early", "mid", "late"]:
            n = len(phase_agreed[phase])
            rate = phase_rates[phase]
            print(f"    {phase:>5}: {rate:.1%} ({n} moves)")
        print()

    # ---- Save results ----
    output_dir = Path(args.output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "layer3_results.json"

    # Make results serializable
    serializable = json.loads(json.dumps(results, default=str))
    with open(results_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"  Results saved to: {results_path}")

    print("\n  Done!")


if __name__ == "__main__":
    main()

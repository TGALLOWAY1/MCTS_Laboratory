#!/usr/bin/env python3
"""Single-command tournament runner with TrueSkill ratings and game logging.

Runs N complete 4-player games between agent variants, producing:
- TrueSkill leaderboard (sorted by conservative estimate mu - 3*sigma)
- Per-agent score statistics with standard error
- Score distribution per seat position (detects first-player advantage)
- Score margins (competitive vs blowout games)
- Per-move game logs with MCTS diagnostics (optional)
- Full summary in JSON and Markdown

Usage:
    python scripts/run_tournament.py
    python scripts/run_tournament.py --num-games 50 --verbose
    python scripts/run_tournament.py --num-games 100 --enable-logging
    python scripts/run_tournament.py --config scripts/arena_config.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.tournament.arena_runner import RunConfig, run_experiment


# Default 4-agent tournament: MCTS vs FastMCTS vs Heuristic vs Random
DEFAULT_CONFIG = {
    "agents": [
        {
            "name": "mcts_100",
            "type": "mcts",
            "thinking_time_ms": 500,
            "params": {"iterations": 100, "deterministic_time_budget": True, "iterations_per_ms": 0.2},
        },
        {
            "name": "fast_mcts_500",
            "type": "fast_mcts",
            "thinking_time_ms": 500,
            "params": {"iterations": 500, "deterministic_time_budget": True, "iterations_per_ms": 1.0},
        },
        {
            "name": "heuristic",
            "type": "heuristic",
            "params": {},
        },
        {
            "name": "random",
            "type": "random",
            "params": {},
        },
    ],
    "num_games": 20,
    "seed": 42,
    "seat_policy": "round_robin",
}


def main():
    parser = argparse.ArgumentParser(description="Run a Blokus tournament with TrueSkill ratings")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to arena config JSON (overrides default agents)")
    parser.add_argument("--num-games", type=int, default=None,
                        help="Number of games to play (default: 20)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--seat-policy", choices=["round_robin", "randomized"],
                        default=None, help="Seat assignment policy")
    parser.add_argument("--enable-logging", action="store_true",
                        help="Enable per-move game logging with MCTS diagnostics")
    parser.add_argument("--verbose", action="store_true", help="Print per-game results")
    parser.add_argument("--output-root", type=str, default="arena_runs",
                        help="Output directory root")
    args = parser.parse_args()

    # Load config
    if args.config:
        with open(args.config) as f:
            config_dict = json.load(f)
    else:
        config_dict = dict(DEFAULT_CONFIG)

    # Apply CLI overrides
    if args.num_games is not None:
        config_dict["num_games"] = args.num_games
    if args.seed is not None:
        config_dict["seed"] = args.seed
    if args.seat_policy is not None:
        config_dict["seat_policy"] = args.seat_policy
    config_dict["output_root"] = args.output_root

    run_config = RunConfig.from_dict(config_dict)

    print(f"Running tournament: {run_config.num_games} games, "
          f"agents: {', '.join(a.name for a in run_config.agents)}")
    print(f"Seat policy: {run_config.seat_policy}, seed: {run_config.seed}")
    if args.enable_logging:
        print("Game logging: ENABLED (MCTS diagnostics will be recorded)")
    print()

    result = run_experiment(
        run_config,
        verbose=args.verbose,
        enable_game_logging=args.enable_logging,
    )

    # Print summary
    run_dir = result["run_dir"]
    summary = result["summary"]

    print(f"\n{'='*60}")
    print(f"Tournament Complete — {summary['completed_games']}/{summary['num_games']} games")
    print(f"Run ID: {result['run_id']}")
    print(f"Output: {run_dir}")
    print(f"{'='*60}\n")

    # TrueSkill Leaderboard
    ts = summary.get("trueskill_ratings", {})
    if ts.get("leaderboard"):
        print("TrueSkill Leaderboard (sorted by conservative estimate mu - 3*sigma):")
        print(f"  {'Rank':<6} {'Agent':<20} {'mu':<10} {'sigma':<10} {'Conservative':<15} {'Games':<8}")
        print(f"  {'-'*69}")
        for entry in ts["leaderboard"]:
            print(f"  {entry['rank']:<6} {entry['agent_id']:<20} "
                  f"{entry['mu']:<10.2f} {entry['sigma']:<10.2f} "
                  f"{entry['conservative']:<15.2f} {entry['games_played']:<8}")
        print(f"  Converged: {ts['converged']}")
        print()

    # Win rates
    print("Win Rates:")
    for agent, stats in sorted(summary["win_stats"].items()):
        print(f"  {agent}: {stats['win_rate']:.3f} "
              f"({int(stats['outright_wins'])} wins, {int(stats['shared_wins'])} shared)")
    print()

    # Score stats
    print("Score Statistics:")
    for agent, stats in sorted(summary["score_stats"].items()):
        mean = stats.get("mean")
        std = stats.get("std")
        if mean is not None:
            se = std / (stats["count"] ** 0.5) if std and stats["count"] > 0 else 0
            print(f"  {agent}: {mean:.1f} ± {se:.1f} (n={stats['count']})")
    print()

    # Score margins
    margins = summary.get("score_margins", {})
    if margins.get("n_games", 0) > 0:
        print(f"Score Margins: mean={margins['mean_margin']}, "
              f"median={margins['median_margin']}, "
              f"range=[{margins['min_margin']}, {margins['max_margin']}]")
        print()

    print(f"Full summary: {run_dir}/summary.md")
    print(f"JSON data:    {run_dir}/summary.json")
    if args.enable_logging:
        print(f"Game logs:    {run_dir}/game_logs/steps.jsonl")


if __name__ == "__main__":
    main()

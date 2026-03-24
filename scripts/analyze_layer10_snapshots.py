#!/usr/bin/env python3
"""Layer 10.3: Phase-dependent analysis of optimal rollout depth.

Analyzes snapshot data from Layer 10.1 and 10.2 arena runs to determine
whether the optimal iteration/depth split changes across game phases.

Usage:
    python scripts/analyze_layer10_snapshots.py --run-dir arena_runs/<run_id>
    python scripts/analyze_layer10_snapshots.py --run-dir arena_runs/<run_id1> arena_runs/<run_id2>
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_snapshots(run_dir: Path) -> list:
    """Load snapshot rows from a run directory."""
    csv_path = run_dir / "snapshots.csv"
    if not csv_path.exists():
        print(f"Warning: No snapshots.csv in {run_dir}")
        return []
    rows = []
    with csv_path.open("r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def load_game_results(run_dir: Path) -> dict:
    """Load game results to get final scores and winners per game."""
    games_path = run_dir / "games.jsonl"
    if not games_path.exists():
        return {}
    results = {}
    with games_path.open("r") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            game_id = record.get("game_id", "")
            results[game_id] = record
    return results


def analyze_phase_performance(run_dirs: list):
    """Analyze agent performance at each checkpoint ply."""
    all_snapshots = []
    all_game_results = {}

    for rd in run_dirs:
        run_dir = Path(rd)
        snapshots = load_snapshots(run_dir)
        game_results = load_game_results(run_dir)
        all_snapshots.extend(snapshots)
        all_game_results.update(game_results)

    if not all_snapshots:
        print("No snapshot data found.")
        return

    # Enrich snapshots with final game outcomes
    for snap in all_snapshots:
        game_id = snap.get("game_id", "")
        game = all_game_results.get(game_id, {})
        if game:
            agent_scores = game.get("agent_scores", {})
            agent_name = snap.get("agent_name", "")
            snap["final_agent_score"] = agent_scores.get(agent_name)
            snap["winner_agents"] = game.get("winner_agents", [])
            snap["is_winner"] = agent_name in game.get("winner_agents", [])

    # Group by checkpoint_ply and agent_name
    phase_agent_scores = defaultdict(lambda: defaultdict(list))
    phase_agent_wins = defaultdict(lambda: defaultdict(int))
    phase_agent_games = defaultdict(lambda: defaultdict(int))

    for snap in all_snapshots:
        ply = int(snap.get("checkpoint_ply", 0))
        agent = snap.get("agent_name", "unknown")
        score = snap.get("final_agent_score")
        is_winner = snap.get("is_winner", False)

        if score is not None:
            phase_agent_scores[ply][agent].append(float(score))
        phase_agent_games[ply][agent] += 1
        if is_winner:
            phase_agent_wins[ply][agent] += 1

    # Print results
    plys = sorted(phase_agent_scores.keys())
    agents = sorted(
        {a for ply_agents in phase_agent_scores.values() for a in ply_agents}
    )

    if not agents:
        print("No agent data found in snapshots.")
        return

    # Determine game phase labels
    def phase_label(ply):
        if ply < 20:
            return "early"
        elif ply < 44:
            return "mid"
        else:
            return "late"

    # Header
    col_width = max(len(a) for a in agents) + 2
    header = f"{'Ply':<6} {'Phase':<7}"
    for agent in agents:
        header += f" {agent:>{col_width}}"
    print("=" * len(header))
    print("Agent Mean Final Score by Checkpoint Ply")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for ply in plys:
        row = f"{ply:<6} {phase_label(ply):<7}"
        scores = {}
        for agent in agents:
            agent_scores = phase_agent_scores[ply].get(agent, [])
            if agent_scores:
                mean = sum(agent_scores) / len(agent_scores)
                scores[agent] = mean
                row += f" {mean:>{col_width}.1f}"
            else:
                row += f" {'—':>{col_width}}"

        # Mark the best agent at this ply
        if scores:
            best = max(scores, key=scores.get)
            row += f"  <- {best}"
        print(row)

    # Win rate summary
    print()
    print("=" * len(header))
    print("Agent Win Rate by Checkpoint Ply")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for ply in plys:
        row = f"{ply:<6} {phase_label(ply):<7}"
        rates = {}
        for agent in agents:
            wins = phase_agent_wins[ply].get(agent, 0)
            games = phase_agent_games[ply].get(agent, 0)
            if games > 0:
                rate = wins / games
                rates[agent] = rate
                pct = f"{rate*100:.0f}%"
                row += f" {pct:>{col_width}}"
            else:
                row += f" {'—':>{col_width}}"

        if rates:
            best = max(rates, key=rates.get)
            row += f"  <- {best}"
        print(row)

    # Overall summary
    print()
    print("=" * 60)
    print("Overall Summary")
    print("=" * 60)
    for agent in agents:
        all_scores = []
        total_wins = 0
        total_games = 0
        for ply in plys:
            all_scores.extend(phase_agent_scores[ply].get(agent, []))
            total_wins += phase_agent_wins[ply].get(agent, 0)
            total_games += phase_agent_games[ply].get(agent, 0)
        if all_scores:
            mean = sum(all_scores) / len(all_scores)
            win_rate = total_wins / total_games if total_games > 0 else 0
            print(
                f"  {agent:<30} avg_score={mean:.1f}  "
                f"win_rate={win_rate*100:.0f}%  "
                f"n={len(all_scores)}"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Layer 10.3: Phase-dependent optimal depth analysis"
    )
    parser.add_argument(
        "--run-dir",
        nargs="+",
        required=True,
        help="One or more arena run directories to analyze",
    )
    args = parser.parse_args()

    analyze_phase_performance(args.run_dir)


if __name__ == "__main__":
    main()

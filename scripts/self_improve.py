#!/usr/bin/env python
"""Layer 9.4 — Self-Improvement Loop.

Runs an arena tournament, parses results, and appends metrics to a
tracking log so improvement trends can be monitored over time.

Usage:
    python scripts/self_improve.py --config scripts/arena_config_layer9_adaptive.json
    python scripts/self_improve.py --config scripts/arena_config_layer9_adaptive.json --num-games 20
    python scripts/self_improve.py --log data/self_improve_log.json --show

The ``--show`` flag prints the improvement history without running a new tournament.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_LOG = "data/self_improve_log.json"


def _find_latest_run(output_root: str = "arena_runs") -> str | None:
    """Return the path to the most recently created arena run directory."""
    root = Path(output_root)
    if not root.exists():
        return None
    runs = sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for r in runs:
        if r.is_dir() and (r / "summary.json").exists():
            return str(r)
    return None


def run_arena(config_path: str, num_games: int | None = None) -> str:
    """Run an arena experiment and return the output directory path."""
    cmd = [sys.executable, "scripts/arena.py", "--config", config_path]
    if num_games is not None:
        cmd.extend(["--num-games", str(num_games)])
    print(f"[self_improve] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"[self_improve] Arena exited with code {result.returncode}")
        sys.exit(1)
    run_dir = _find_latest_run()
    if run_dir is None:
        print("[self_improve] ERROR: Could not find arena output directory.")
        sys.exit(1)
    print(f"[self_improve] Arena output: {run_dir}")
    return run_dir


def parse_summary(run_dir: str) -> dict:
    """Extract key metrics from an arena summary.json."""
    summary_path = os.path.join(run_dir, "summary.json")
    with open(summary_path) as f:
        data = json.load(f)

    agents = {}
    for agent_name, agent_data in data.get("agents", {}).items():
        agents[agent_name] = {
            "wins": agent_data.get("wins", 0),
            "win_rate": agent_data.get("win_rate", 0.0),
            "avg_score": agent_data.get("avg_score", 0.0),
            "trueskill_mu": agent_data.get("trueskill_mu"),
            "trueskill_sigma": agent_data.get("trueskill_sigma"),
        }

    return {
        "num_games": data.get("num_games", 0),
        "agents": agents,
    }


def append_log(log_path: str, entry: dict) -> list:
    """Append a new entry to the improvement log and return full history."""
    log = []
    if os.path.exists(log_path):
        with open(log_path) as f:
            log = json.load(f)

    log.append(entry)

    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    return log


def show_history(log_path: str) -> None:
    """Print the improvement history in a readable format."""
    if not os.path.exists(log_path):
        print(f"[self_improve] No log found at {log_path}")
        return

    with open(log_path) as f:
        log = json.load(f)

    if not log:
        print("[self_improve] Log is empty.")
        return

    print(f"\n{'='*70}")
    print(f" Self-Improvement History — {len(log)} run(s)")
    print(f"{'='*70}")

    for i, entry in enumerate(log):
        ts = entry.get("timestamp", "?")
        games = entry.get("num_games", "?")
        print(f"\n--- Run {i+1} ({ts}, {games} games) ---")
        agents = entry.get("agents", {})
        # Sort by win rate descending
        ranked = sorted(agents.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True)
        for name, stats in ranked:
            wr = stats.get("win_rate", 0) * 100
            avg = stats.get("avg_score", 0)
            mu = stats.get("trueskill_mu")
            mu_str = f"  μ={mu:.1f}" if mu is not None else ""
            print(f"  {name:30s}  WR={wr:5.1f}%  AvgScore={avg:6.1f}{mu_str}")

    # Compare latest to first
    if len(log) >= 2:
        print(f"\n{'='*70}")
        print(" Trend (first → latest)")
        print(f"{'='*70}")
        first_agents = log[0].get("agents", {})
        last_agents = log[-1].get("agents", {})
        for name in last_agents:
            if name in first_agents:
                delta_wr = (last_agents[name].get("win_rate", 0) - first_agents[name].get("win_rate", 0)) * 100
                sign = "+" if delta_wr >= 0 else ""
                print(f"  {name:30s}  ΔWR={sign}{delta_wr:5.1f}pp")

    print()


def main():
    parser = argparse.ArgumentParser(description="Layer 9.4 Self-Improvement Loop")
    parser.add_argument("--config", type=str, default="scripts/arena_config_layer9_adaptive.json",
                        help="Arena config JSON path")
    parser.add_argument("--num-games", type=int, default=None,
                        help="Override number of games")
    parser.add_argument("--log", type=str, default=DEFAULT_LOG,
                        help="Path to improvement tracking log (JSON)")
    parser.add_argument("--show", action="store_true",
                        help="Show improvement history and exit (no new run)")
    args = parser.parse_args()

    if args.show:
        show_history(args.log)
        return

    run_dir = run_arena(args.config, args.num_games)
    metrics = parse_summary(run_dir)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": args.config,
        "run_dir": run_dir,
        **metrics,
    }

    history = append_log(args.log, entry)
    print(f"\n[self_improve] Logged run #{len(history)} to {args.log}")
    show_history(args.log)


if __name__ == "__main__":
    main()

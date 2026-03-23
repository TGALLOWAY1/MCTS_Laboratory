#!/usr/bin/env python3
"""Merge heuristic games from multiple run dirs into one for baseline analysis.

Usage:
    python scripts/merge_heuristic_runs.py baseline_runs/layer1_20260322_154726

Merges all games from heuristic/<run_id>/games.jsonl into the run dir with
the most games. After running, --resume will see 100+ heuristic games and
skip to analysis.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.tournament.arena_stats import load_games_jsonl


def merge_heuristic_runs(output_dir: Path) -> int:
    """Merge heuristic games from all run dirs into the largest one. Returns merged count."""
    heuristic_parent = output_dir / "heuristic"
    if not heuristic_parent.exists():
        print(f"No heuristic dir at {heuristic_parent}")
        return 0

    subdirs = [d for d in heuristic_parent.iterdir() if d.is_dir()]
    if not subdirs:
        print("No heuristic run dirs found")
        return 0

    all_records = []
    for subdir in subdirs:
        games_path = subdir / "games.jsonl"
        if games_path.exists():
            records = load_games_jsonl(games_path)
            all_records.extend(records)

    if not all_records:
        print("No valid game records found")
        return 0

    # Target = dir with most games (will be overwritten with merged set)
    target = max(subdirs, key=lambda d: len(load_games_jsonl(d / "games.jsonl")))
    target_path = target / "games.jsonl"

    with target_path.open("w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    print(f"Merged {len(all_records)} heuristic games into {target.name}/games.jsonl")
    return len(all_records)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/merge_heuristic_runs.py <output_dir>")
        sys.exit(1)
    output_dir = Path(sys.argv[1])
    if not output_dir.exists():
        print(f"Directory not found: {output_dir}")
        sys.exit(1)
    n = merge_heuristic_runs(output_dir)
    sys.exit(0 if n >= 100 else 1)

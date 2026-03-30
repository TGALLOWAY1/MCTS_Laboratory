#!/usr/bin/env python3
"""Generate MCTS visit-count heatmap animation for a Blokus game.

Usage:
    # Run a game and generate heatmap video:
    python scripts/generate_mcts_heatmap_video.py --config scripts/arena_config.json

    # Generate from existing heatmap data:
    python scripts/generate_mcts_heatmap_video.py --data-dir heatmap_data/game_001

    # Filter to a single player:
    python scripts/generate_mcts_heatmap_video.py --config scripts/arena_config.json --player 1

    # Custom thinking time and output:
    python scripts/generate_mcts_heatmap_video.py --config scripts/arena_config.json \\
        --thinking-time-ms 50 --output-root heatmap_output --fps 3
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analytics.heatmap.renderer import render_all
from analytics.tournament.arena_runner import (
    AgentConfig,
    RunConfig,
    SnapshotConfig,
    build_agent,
    run_single_game,
)
from engine.board import Player


def _load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return json.load(f)


def _run_game_with_heatmap(
    config_path: Path,
    output_root: Path,
    thinking_time_ms: int | None = None,
    game_seed: int | None = None,
    verbose: bool = True,
) -> Path:
    """Run a single game and collect heatmap data."""
    raw_config = _load_config(config_path)

    agents_raw = raw_config.get("agents", [])
    if not agents_raw:
        raise ValueError("Config has no agents defined")

    # Build agent configs
    agent_configs = {}
    for a in agents_raw:
        name = a["name"]
        cfg = AgentConfig(
            name=name,
            type=a["type"],
            thinking_time_ms=thinking_time_ms or a.get("thinking_time_ms"),
            params=a.get("params", {}),
        )
        agent_configs[name] = cfg

    # Build seat assignment (first 4 agents, cycling if fewer)
    agent_names = list(agent_configs.keys())
    seat_assignment = {}
    for i, player in enumerate([Player.RED, Player.BLUE, Player.YELLOW, Player.GREEN]):
        seat_assignment[str(player.value)] = agent_names[i % len(agent_names)]

    seed = game_seed or raw_config.get("seed", int(time.time()))
    game_id = f"heatmap_{seed}"
    heatmap_dir = output_root / "heatmap_data" / game_id

    run_config = RunConfig(
        agents=[agent_configs[n] for n in agent_names],
        num_games=1,
        seed=seed,
        seat_policy="round_robin",
        output_root=str(output_root / "arena_runs"),
        max_turns=raw_config.get("max_turns", 2500),
        snapshots=SnapshotConfig(enabled=False, strategy="fixed_ply", checkpoints=[]),
    )

    if verbose:
        print(f"Running game with seed {seed}...")
        print(f"Agents: {list(agent_configs.keys())}")
        print(f"Seats: {seat_assignment}")
        print(f"Heatmap data → {heatmap_dir}")

    game_record, _ = run_single_game(
        run_id=game_id,
        game_index=0,
        game_seed=seed,
        run_config=run_config,
        seat_assignment=seat_assignment,
        agent_configs=agent_configs,
        verbose=verbose,
        heatmap_output_dir=heatmap_dir,
    )

    if verbose:
        scores = game_record.get("final_scores", {})
        print(f"Game finished. Scores: {scores}")

    return heatmap_dir


def main():
    parser = argparse.ArgumentParser(
        description="Generate MCTS visit-count heatmap animation",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--config",
        type=Path,
        help="Arena config JSON to run a game and collect data",
    )
    group.add_argument(
        "--data-dir",
        type=Path,
        help="Existing heatmap data directory to render from",
    )

    parser.add_argument("--player", type=int, default=None, help="Filter to player ID (1-4)")
    parser.add_argument("--output-root", type=Path, default=Path("heatmap_output"), help="Output directory")
    parser.add_argument("--thinking-time-ms", type=int, default=None, help="Override thinking time")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for game")
    parser.add_argument("--fps", type=int, default=2, help="Frames per second for video")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    if args.config:
        data_dir = _run_game_with_heatmap(
            config_path=args.config,
            output_root=args.output_root,
            thinking_time_ms=args.thinking_time_ms,
            game_seed=args.seed,
            verbose=not args.quiet,
        )
    else:
        data_dir = args.data_dir
        if not data_dir.exists():
            print(f"Error: data directory not found: {data_dir}", file=sys.stderr)
            sys.exit(1)

    if not args.quiet:
        print(f"\nRendering heatmap animation from {data_dir}...")

    result = render_all(
        data_dir=data_dir,
        output_root=args.output_root,
        player_filter=args.player,
        fps=args.fps,
    )

    if not args.quiet:
        print(f"Done! Output: {result}")


if __name__ == "__main__":
    main()

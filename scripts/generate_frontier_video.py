#!/usr/bin/env python3
"""Generate a frontier-overlay video for Blokus board snapshots.

Usage:
    # Run a game, capture turn data, and render Red's frontier turns to video
    python scripts/generate_frontier_video.py --config scripts/arena_config_heatmap_fast.json

    # Render from an existing captured turn-data directory
    python scripts/generate_frontier_video.py --data-dir frontier_output/heatmap_data/heatmap_42
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict

# Ensure project root is on the path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analytics.heatmap.renderer import (
    PLAYER_NAMES,
    compute_frontier_cells,
    generate_video,
    render_board_with_frontier_image,
)
from analytics.tournament.arena_runner import AgentConfig, RunConfig, SnapshotConfig, run_single_game
from engine.board import Player


def _load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as handle:
        return json.load(handle)


def _run_game_and_capture_turn_data(
    config_path: Path,
    output_root: Path,
    thinking_time_ms: int | None = None,
    game_seed: int | None = None,
    verbose: bool = True,
) -> Path:
    """Run a single game and capture per-turn board snapshots."""
    raw_config = _load_config(config_path)

    agents_raw = raw_config.get("agents", [])
    if not agents_raw:
        raise ValueError("Config has no agents defined")

    agent_configs: Dict[str, AgentConfig] = {}
    for agent in agents_raw:
        name = agent["name"]
        agent_configs[name] = AgentConfig(
            name=name,
            type=agent["type"],
            thinking_time_ms=thinking_time_ms or agent.get("thinking_time_ms"),
            params=agent.get("params", {}),
        )

    # Support configs that define fewer than four unique agents by cycling seats.
    agent_names = list(agent_configs.keys())
    seat_assignment = {}
    for i, player in enumerate([Player.RED, Player.BLUE, Player.YELLOW, Player.GREEN]):
        seat_assignment[str(player.value)] = agent_names[i % len(agent_names)]

    seed = game_seed or raw_config.get("seed", int(time.time()))
    game_id = f"frontier_{seed}"
    turn_data_dir = output_root / "heatmap_data" / game_id

    run_config = RunConfig(
        agents=[agent_configs[name] for name in agent_names],
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
        print(f"Turn data -> {turn_data_dir}")

    record, _ = run_single_game(
        run_id=game_id,
        game_index=0,
        game_seed=seed,
        run_config=run_config,
        seat_assignment=seat_assignment,
        agent_configs=agent_configs,
        verbose=verbose,
        heatmap_output_dir=turn_data_dir,
    )

    if verbose:
        print(f"Game finished. Scores: {record.get('final_scores', {})}")

    return turn_data_dir


def render_frontier_video(
    data_dir: Path,
    output_root: Path,
    frontier_player: int = Player.RED.value,
    turn_player: int | None = Player.RED.value,
    fps: int = 2,
    verbose: bool = True,
) -> Path:
    """Render board frames with one player's frontier highlighted and compile a video."""
    from PIL import Image

    turn_files = sorted(data_dir.glob("turn_*.json"))
    if not turn_files:
        raise FileNotFoundError(f"No turn data found in {data_dir}")

    boards_dir = output_root / "boards" / data_dir.name
    frames_dir = output_root / "frames" / data_dir.name
    videos_dir = output_root / "videos"
    for directory in [boards_dir, frames_dir, videos_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    frame_idx = 0
    for turn_file in turn_files:
        turn_data = _load_config(turn_file)

        if turn_player is not None and turn_data.get("player") != turn_player:
            continue

        turn_number = int(turn_data["turn"])
        active_player = int(turn_data.get("player", 0))
        board_grid = turn_data["board_grid"]
        frontier_cells = compute_frontier_cells(board_grid, frontier_player)
        frontier_name = PLAYER_NAMES.get(frontier_player, str(frontier_player))
        active_name = PLAYER_NAMES.get(active_player, str(active_player))
        title = (
            f"Turn {turn_number} | {active_name} to move | "
            f"{frontier_name} frontier: {len(frontier_cells)}"
        )

        board_img = render_board_with_frontier_image(
            board_grid=board_grid,
            frontier_cells=frontier_cells,
            frontier_player=frontier_player,
            title=title,
        )

        board_path = boards_dir / f"turn_{turn_number:03d}.png"
        Image.fromarray(board_img).save(board_path)

        frame_path = frames_dir / f"frame_{frame_idx:03d}.png"
        Image.fromarray(board_img).save(frame_path)
        frame_idx += 1

    if frame_idx == 0:
        raise RuntimeError("No frames generated. Check the selected turn/player filters.")

    output_stem = videos_dir / f"{data_dir.name}_{PLAYER_NAMES[frontier_player].lower()}_frontier"
    result = generate_video(frames_dir, output_stem, fps=fps)

    if verbose:
        print(f"Generated {frame_idx} frames in {frames_dir}")
        print(f"Video output: {result}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a board video with frontier cells highlighted.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--config",
        type=Path,
        help="Arena config JSON to run a game and capture turn data",
    )
    group.add_argument(
        "--data-dir",
        type=Path,
        help="Existing turn-data directory containing turn_XXX.json files",
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("frontier_output"),
        help="Output directory for frames and video",
    )
    parser.add_argument(
        "--turn-player",
        type=int,
        default=Player.RED.value,
        help="Only render turns where this player is to move (default: 1 / Red)",
    )
    parser.add_argument(
        "--frontier-player",
        type=int,
        default=Player.RED.value,
        help="Highlight this player's frontier cells (default: 1 / Red)",
    )
    parser.add_argument("--thinking-time-ms", type=int, default=None, help="Override thinking time")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for game generation")
    parser.add_argument("--fps", type=int, default=2, help="Frames per second for output video")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    if args.config:
        data_dir = _run_game_and_capture_turn_data(
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

    render_frontier_video(
        data_dir=data_dir,
        output_root=args.output_root,
        frontier_player=args.frontier_player,
        turn_player=args.turn_player,
        fps=args.fps,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()

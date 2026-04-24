#!/usr/bin/env python3
"""Plot legal move counts per player per turn for a captured Blokus game.

Usage:
    # Run a game, capture turn data, and plot legal move counts
    python3 scripts/plot_legal_move_counts.py --config scripts/arena_config_heatmap_fast.json

    # Plot from an existing turn-data directory
    python3 scripts/plot_legal_move_counts.py --data-dir frontier_output/heatmap_data/frontier_42
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import numpy as np

# Ensure project root is on the path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analytics.heatmap.renderer import PLAYER_NAMES
from analytics.plot_style import (
    PLAYER_COLORS as LAB_PLAYER_COLORS,
    apply_lab_style,
    save_figure,
    style_axes,
    style_legend,
)
from engine.bitboard import coord_to_bit
from engine.board import Board, Player
from engine.move_generator import LegalMoveGenerator
from scripts.generate_frontier_video import _load_config, _run_game_and_capture_turn_data

PLAYER_COLORS = {player: LAB_PLAYER_COLORS[player.name] for player in Player}


def reconstruct_board_from_turn_data(turn_data: dict) -> Board:
    """Rebuild a Board object from a saved turn-data snapshot."""
    board = Board()
    grid = np.array(turn_data["board_grid"], dtype=int)
    board.grid = grid

    used_pieces_raw = turn_data.get("used_pieces", {})
    board.player_pieces_used = {
        player: set(used_pieces_raw.get(str(player.value), []))
        for player in Player
    }
    board.player_first_move = {
        player: len(board.player_pieces_used[player]) == 0
        for player in Player
    }
    board.current_player = Player(int(turn_data["player"]))
    board.move_count = max(0, int(turn_data["turn"]) - 1)
    board.game_over = False

    board.occupied_bits = 0
    board.player_bits = defaultdict(int)
    for row in range(board.SIZE):
        for col in range(board.SIZE):
            cell = int(grid[row, col])
            if cell == 0:
                continue
            bit = coord_to_bit(row, col)
            board.occupied_bits |= bit
            board.player_bits[Player(cell)] |= bit

    board.player_frontiers = {player: set() for player in Player}
    for player in Player:
        if board.player_first_move[player]:
            start_corner = board.player_start_corners[player]
            board.player_frontiers[player].add((start_corner.row, start_corner.col))
        else:
            board.player_frontiers[player] = board._compute_full_frontier(player)

    return board


def compute_legal_move_counts(data_dir: Path) -> List[Dict[str, int]]:
    """Compute per-turn legal move counts for all players from saved turn data."""
    turn_files = sorted(data_dir.glob("turn_*.json"))
    if not turn_files:
        raise FileNotFoundError(f"No turn data found in {data_dir}")

    generator = LegalMoveGenerator()
    counts: List[Dict[str, int]] = []

    for turn_file in turn_files:
        turn_data = _load_config(turn_file)
        board = reconstruct_board_from_turn_data(turn_data)
        row: Dict[str, int] = {
            "turn": int(turn_data["turn"]),
            "player": int(turn_data["player"]),
        }
        for player in Player:
            row[player.name] = len(generator.get_legal_moves(board, player))
        counts.append(row)

    return counts


def write_counts_csv(counts: List[Dict[str, int]], output_path: Path) -> Path:
    """Write per-turn legal move counts to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["turn", "player", "RED", "BLUE", "YELLOW", "GREEN"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(counts)
    return output_path


def plot_legal_move_counts(
    counts: List[Dict[str, int]],
    output_path: Path,
    title: str,
) -> Path:
    """Render a line chart of legal move counts per player per turn."""
    import matplotlib.pyplot as plt

    apply_lab_style()

    turns = [row["turn"] for row in counts]
    fig, ax = plt.subplots(figsize=(12, 6))
    style_axes(ax)

    for player in Player:
        player_name = player.name
        ax.plot(
            turns,
            [row[player_name] for row in counts],
            label=PLAYER_NAMES[player.value],
            color=PLAYER_COLORS[player],
            linewidth=2.2,
        )

    ax.set_title(title, pad=14)
    ax.set_xlabel("Turn")
    ax.set_ylabel("Legal move count")
    style_legend(ax.legend(loc="best"))

    return save_figure(fig, output_path)


def render_legal_move_count_plot(
    data_dir: Path,
    output_root: Path,
    verbose: bool = True,
) -> Path:
    """Compute counts, save CSV, and render the line chart."""
    counts = compute_legal_move_counts(data_dir)
    plots_dir = output_root / "plots"
    csv_dir = output_root / "csv"

    csv_path = write_counts_csv(
        counts,
        csv_dir / f"{data_dir.name}_legal_move_counts.csv",
    )
    plot_path = plot_legal_move_counts(
        counts,
        plots_dir / f"{data_dir.name}_legal_move_counts.png",
        title=f"Legal Move Count per Player per Turn ({data_dir.name})",
    )

    if verbose:
        print(f"Saved CSV: {csv_path}")
        print(f"Saved plot: {plot_path}")

    return plot_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot legal move counts per player per turn.",
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
        help="Output directory for plot artifacts",
    )
    parser.add_argument("--thinking-time-ms", type=int, default=None, help="Override thinking time")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for game generation")
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

    render_legal_move_count_plot(
        data_dir=data_dir,
        output_root=args.output_root,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()

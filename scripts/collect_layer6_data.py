#!/usr/bin/env python
"""Collect self-play data for Layer 6 evaluation function refinement.

Runs MCTS self-play games and extracts **both** feature sets at every
checkpoint interval:

1. The 7 ``BlokusStateEvaluator`` features (used during MCTS rollouts).
2. The 35 ``analytics.winprob.features`` features (richer candidate set).

Each row also records the game's final score so downstream regression can
learn: ``actual_final_score ~ f(features)``.

Example
-------
# Quick test (20 games, sequential)
python scripts/collect_layer6_data.py --num-games 20 --workers 1

# Full collection (700 games  ~10k+ states, 4 workers)
python scripts/collect_layer6_data.py --num-games 700 --workers 4
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from analytics.winprob.features import (
    SNAPSHOT_FEATURE_COLUMNS,
    build_snapshot_runtime_context,
    extract_player_snapshot_features,
)
from engine.board import Board, Player
from engine.game import BlokusGame
from engine.move_generator import LegalMoveGenerator, get_shared_generator
from mcts.state_evaluator import BlokusStateEvaluator, FEATURE_NAMES

# Prefix state-evaluator columns to avoid name collisions with winprob features
SE_PREFIX = "se_"

# ---------------------------------------------------------------------------
# Agent helpers
# ---------------------------------------------------------------------------


def _make_agent(agent_type: str, thinking_time_ms: int, seed: Optional[int]):
    """Construct an agent by type string."""
    if agent_type == "mcts":
        from mcts.mcts_agent import MCTSAgent

        return MCTSAgent(
            iterations=999_999,
            time_limit=thinking_time_ms / 1000.0,
            seed=seed,
        )
    elif agent_type == "heuristic":
        from agents.heuristic_agent import HeuristicAgent

        return HeuristicAgent(seed=seed)
    elif agent_type == "random":
        import random as _random

        class _RandomAgent:
            def __init__(self, s):
                self._rng = _random.Random(s)

            def select_action(self, board, player, legal_moves):
                return self._rng.choice(legal_moves) if legal_moves else None

        return _RandomAgent(seed)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def _agent_select(agent, board: Board, player: Player, legal_moves, thinking_time_ms: int):
    """Unified action selection across agent types."""
    if hasattr(agent, "think"):
        result = agent.think(board, player, legal_moves, thinking_time_ms)
        return result["move"]
    return agent.select_action(board, player, legal_moves)


# ---------------------------------------------------------------------------
# Single-game worker
# ---------------------------------------------------------------------------


def _play_one_game(
    game_index: int,
    agent_type: str,
    thinking_time_ms: int,
    checkpoint_interval: int,
    seed: int,
    run_id: str,
    max_turns: int,
) -> List[Dict[str, Any]]:
    """Play a single 4-player game and return snapshot rows with dual features."""
    game_seed = seed + game_index

    agents = {
        p: _make_agent(agent_type, thinking_time_ms, game_seed + p.value)
        for p in Player
    }

    game = BlokusGame(enable_telemetry=False)
    board = game.board
    move_gen = get_shared_generator()
    state_eval = BlokusStateEvaluator()  # default weights — we only need raw features

    turn_index = 0
    consecutive_passes = 0
    snapshots: List[Dict[str, Any]] = []
    checkpoint_counter = 0

    while not board.game_over and turn_index < max_turns:
        player = board.current_player
        legal_moves = move_gen.get_legal_moves(board, player)

        if not legal_moves:
            consecutive_passes += 1
            if consecutive_passes >= 4:
                board.game_over = True
                break
            board._update_current_player()
            turn_index += 1
            continue

        consecutive_passes = 0

        # --- Checkpoint: extract features for ALL 4 players ---
        if turn_index > 0 and turn_index % checkpoint_interval == 0:
            ctx = build_snapshot_runtime_context(
                board, turn_index=turn_index, max_turns=max_turns
            )
            for p in Player:
                # Winprob features (35 columns)
                wp_features = extract_player_snapshot_features(
                    board, player=p, context=ctx, move_generator=move_gen
                )
                # State-evaluator features (7 columns)
                se_features = state_eval.extract_features(board, p)

                row: Dict[str, Any] = {
                    "run_id": run_id,
                    "game_id": game_index,
                    "checkpoint_index": checkpoint_counter,
                    "player_id": p.value,
                    "agent_name": agent_type,
                    "turn_index": turn_index,
                    "final_score": None,  # filled after game ends
                    "phase_board_occupancy": ctx.board_occupancy,
                }
                # Add winprob features
                row.update(wp_features)
                # Add state-evaluator features (prefixed)
                for fname, fval in se_features.items():
                    row[SE_PREFIX + fname] = fval

                snapshots.append(row)
            checkpoint_counter += 1

        # Select and make move
        agent_obj = agents[player]
        move = _agent_select(agent_obj, board, player, legal_moves, thinking_time_ms)

        if move is None:
            board._update_current_player()
        else:
            game.make_move(move, player)

        turn_index += 1

    # Fill in final scores
    result = game.get_game_result()
    for snap in snapshots:
        snap["final_score"] = result.scores[snap["player_id"]]

    return snapshots


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect self-play data for Layer 6 evaluation refinement."
    )
    parser.add_argument("--num-games", type=int, default=700)
    parser.add_argument(
        "--agent-type", type=str, default="mcts",
        choices=["mcts", "heuristic", "random"],
    )
    parser.add_argument("--thinking-time-ms", type=int, default=100)
    parser.add_argument("--checkpoint-interval", type=int, default=4)
    parser.add_argument("--output", type=str, default="data/layer6_selfplay.parquet")
    parser.add_argument("--seed", type=int, default=20260323)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-turns", type=int, default=2500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = f"l6_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    print("=== Layer 6 Self-Play Data Collection ===")
    print(f"  run_id:              {run_id}")
    print(f"  num_games:           {args.num_games}")
    print(f"  agent_type:          {args.agent_type}")
    print(f"  thinking_time_ms:    {args.thinking_time_ms}")
    print(f"  checkpoint_interval: {args.checkpoint_interval}")
    print(f"  workers:             {args.workers}")
    print(f"  seed:                {args.seed}")
    print(f"  output:              {args.output}")
    print()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_snapshots: List[Dict[str, Any]] = []
    t0 = time.time()

    if args.workers <= 1:
        for gi in range(args.num_games):
            snaps = _play_one_game(
                gi, args.agent_type, args.thinking_time_ms,
                args.checkpoint_interval, args.seed, run_id,
                args.max_turns,
            )
            all_snapshots.extend(snaps)
            if (gi + 1) % max(1, args.num_games // 20) == 0:
                elapsed = time.time() - t0
                print(f"  [{gi + 1}/{args.num_games}] {len(all_snapshots)} snapshots ({elapsed:.1f}s)")
    else:
        futures = {}
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            for gi in range(args.num_games):
                fut = executor.submit(
                    _play_one_game,
                    gi, args.agent_type, args.thinking_time_ms,
                    args.checkpoint_interval, args.seed, run_id,
                    args.max_turns,
                )
                futures[fut] = gi

            completed = 0
            for fut in as_completed(futures):
                completed += 1
                snaps = fut.result()
                all_snapshots.extend(snaps)
                if completed % max(1, args.num_games // 20) == 0:
                    elapsed = time.time() - t0
                    print(f"  [{completed}/{args.num_games}] {len(all_snapshots)} snapshots ({elapsed:.1f}s)")

    elapsed = time.time() - t0

    if not all_snapshots:
        print("WARNING: No snapshots generated.")
        return

    df = pd.DataFrame(all_snapshots)

    # Summary stats
    se_cols = [SE_PREFIX + f for f in FEATURE_NAMES]
    wp_present = sum(1 for c in SNAPSHOT_FEATURE_COLUMNS if c in df.columns)
    se_present = sum(1 for c in se_cols if c in df.columns)

    df.to_parquet(str(output_path), index=False)

    print(f"\n=== Collection Complete ===")
    print(f"  Games played:          {args.num_games}")
    print(f"  Total snapshot rows:   {len(df)}")
    print(f"  Unique games:          {df['game_id'].nunique()}")
    print(f"  Winprob features:      {wp_present}/{len(SNAPSHOT_FEATURE_COLUMNS)}")
    print(f"  State-eval features:   {se_present}/{len(FEATURE_NAMES)}")
    print(f"  Checkpoints/game avg:  {df.groupby('game_id')['checkpoint_index'].nunique().mean():.1f}")
    occ = df["phase_board_occupancy"]
    print(f"  Phase distribution:")
    print(f"    early (<0.25):  {(occ < 0.25).sum()}")
    print(f"    mid   (<0.55):  {((occ >= 0.25) & (occ < 0.55)).sum()}")
    print(f"    late  (>=0.55): {(occ >= 0.55).sum()}")
    print(f"  Time elapsed:          {elapsed:.1f}s")
    print(f"  Output:                {output_path}")


if __name__ == "__main__":
    main()

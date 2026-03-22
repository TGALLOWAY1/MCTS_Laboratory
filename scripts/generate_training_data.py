#!/usr/bin/env python
"""Generate self-play training data for win-probability model training.

Runs MCTS-vs-MCTS (or heuristic) games at scale, extracting feature snapshots
at configurable checkpoint intervals.  Output is a parquet file with the schema
expected by ``analytics.winprob.dataset.build_pairwise_dataset``.

Example
-------
python scripts/generate_training_data.py \
    --num-games 500 \
    --agent-type fast_mcts \
    --thinking-time-ms 100 \
    --checkpoint-interval 4 \
    --output data/snapshots.parquet \
    --seed 42 \
    --workers 4
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


# ---------------------------------------------------------------------------
# Agent helpers
# ---------------------------------------------------------------------------

def _make_agent(agent_type: str, thinking_time_ms: int, seed: Optional[int]):
    """Construct an agent by type string."""
    if agent_type == "fast_mcts":
        from agents.fast_mcts_agent import FastMCTSAgent

        return FastMCTSAgent(
            iterations=999_999,
            time_limit=thinking_time_ms / 1000.0,
            seed=seed,
        )
    elif agent_type == "mcts":
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
            def __init__(self, seed):
                self._rng = _random.Random(seed)

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
    mixed_agents: bool,
) -> List[Dict[str, Any]]:
    """Play a single 4-player game and return snapshot rows."""
    game_seed = seed + game_index

    # Create agents (one per seat)
    if mixed_agents:
        agent_types = ["fast_mcts", "heuristic", "mcts", "random"]
        rng = np.random.RandomState(game_seed)
        rng.shuffle(agent_types)
        agents = {}
        for i, p in enumerate(Player):
            a_type = agent_types[i % len(agent_types)]
            agents[p] = (_make_agent(a_type, thinking_time_ms, game_seed + p.value), a_type)
    else:
        agents = {
            p: (_make_agent(agent_type, thinking_time_ms, game_seed + p.value), agent_type)
            for p in Player
        }

    game = BlokusGame(enable_telemetry=False)
    board = game.board
    move_gen = get_shared_generator()

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

        # Checkpoint: extract features for ALL 4 players
        if turn_index > 0 and turn_index % checkpoint_interval == 0:
            ctx = build_snapshot_runtime_context(
                board, turn_index=turn_index, max_turns=max_turns
            )
            for p in Player:
                features = extract_player_snapshot_features(
                    board, player=p, context=ctx, move_generator=move_gen
                )
                row = {
                    "run_id": run_id,
                    "game_id": game_index,
                    "checkpoint_index": checkpoint_counter,
                    "player_id": p.value,
                    "agent_name": agents[p][1],
                    "final_score": None,  # filled after game ends
                    "phase_board_occupancy": ctx.board_occupancy,
                }
                row.update(features)
                snapshots.append(row)
            checkpoint_counter += 1

        # Select and make move
        agent_obj = agents[player][0]
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
        description="Generate self-play training data for win-probability model."
    )
    parser.add_argument("--num-games", type=int, default=500, help="Number of games to play.")
    parser.add_argument(
        "--agent-type",
        type=str,
        default="fast_mcts",
        choices=["fast_mcts", "mcts", "heuristic", "random"],
        help="Agent type for all 4 seats (unless --mixed-agents).",
    )
    parser.add_argument("--thinking-time-ms", type=int, default=100, help="Time budget per move (ms).")
    parser.add_argument("--checkpoint-interval", type=int, default=4, help="Snapshot every N plies.")
    parser.add_argument("--output", type=str, default="data/snapshots.parquet", help="Output parquet path.")
    parser.add_argument("--seed", type=int, default=42, help="Master random seed.")
    parser.add_argument("--workers", type=int, default=4, help="Parallel worker processes.")
    parser.add_argument("--max-turns", type=int, default=2500, help="Max turns per game.")
    parser.add_argument(
        "--mixed-agents",
        action="store_true",
        help="Use a mix of agent types per game for data diversity.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = f"gen_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    print(f"=== Self-Play Data Generation ===")
    print(f"  run_id:              {run_id}")
    print(f"  num_games:           {args.num_games}")
    print(f"  agent_type:          {args.agent_type}")
    print(f"  thinking_time_ms:    {args.thinking_time_ms}")
    print(f"  checkpoint_interval: {args.checkpoint_interval}")
    print(f"  workers:             {args.workers}")
    print(f"  seed:                {args.seed}")
    print(f"  mixed_agents:        {args.mixed_agents}")
    print(f"  output:              {args.output}")
    print()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_snapshots: List[Dict[str, Any]] = []
    t0 = time.time()

    if args.workers <= 1:
        # Sequential
        for gi in range(args.num_games):
            snaps = _play_one_game(
                gi, args.agent_type, args.thinking_time_ms,
                args.checkpoint_interval, args.seed, run_id,
                args.max_turns, args.mixed_agents,
            )
            all_snapshots.extend(snaps)
            if (gi + 1) % max(1, args.num_games // 20) == 0:
                elapsed = time.time() - t0
                print(f"  [{gi + 1}/{args.num_games}] {len(all_snapshots)} snapshots ({elapsed:.1f}s)")
    else:
        # Parallel
        futures = {}
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            for gi in range(args.num_games):
                fut = executor.submit(
                    _play_one_game,
                    gi, args.agent_type, args.thinking_time_ms,
                    args.checkpoint_interval, args.seed, run_id,
                    args.max_turns, args.mixed_agents,
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
        print("WARNING: No snapshots generated. Check agent/game configuration.")
        return

    df = pd.DataFrame(all_snapshots)

    # Validate schema
    expected_cols = [
        "run_id", "game_id", "checkpoint_index", "player_id",
        "agent_name", "final_score", "phase_board_occupancy",
    ] + list(SNAPSHOT_FEATURE_COLUMNS)
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        print(f"WARNING: Missing columns: {missing}")

    df.to_parquet(str(output_path), index=False)

    print(f"\n=== Generation Complete ===")
    print(f"  Games played:   {args.num_games}")
    print(f"  Total snapshots: {len(df)}")
    print(f"  Unique games:    {df['game_id'].nunique()}")
    print(f"  Checkpoints/game: {df.groupby('game_id')['checkpoint_index'].nunique().mean():.1f} avg")
    print(f"  Phase distribution:")
    occ = df["phase_board_occupancy"]
    print(f"    early (<0.33): {(occ < 0.33).sum()}")
    print(f"    mid   (<0.66): {((occ >= 0.33) & (occ < 0.66)).sum()}")
    print(f"    late  (>=0.66): {(occ >= 0.66).sum()}")
    print(f"  Time elapsed:    {elapsed:.1f}s")
    print(f"  Output:          {output_path}")


if __name__ == "__main__":
    main()

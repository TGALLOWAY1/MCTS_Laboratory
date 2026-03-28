#!/usr/bin/env python
"""Generate training data for neural network from agent self-play.

Records raw board states, moves played, and final outcomes at every turn.
Uses the GA-evolved EnhancedHeuristicAgent + default heuristic + random agents.

Usage:
    python scripts/generate_nn_training_data.py --num-games 5000 --output data/nn_training
    python scripts/generate_nn_training_data.py --num-games 10000 --workers 8
"""

import argparse
import multiprocessing
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.enhanced_heuristic_agent import EnhancedHeuristicAgent
from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from engine.board import Player
from engine.game import BlokusGame

EVOLVED_WEIGHTS = {
    "piece_size": 4.186353869233235,
    "corner_creation": 0.47505818308099407,
    "edge_avoidance": -2.096073026902312,
    "center_preference": 4.263163922060554,
    "opponent_blocking": -0.37153835519299516,
    "corners_killed": 1.713864813797406,
    "opponent_proximity": -1.998280477155598,
    "open_space": 0.4363959883717228,
    "piece_versatility": -5.0,
    "blocking_risk": 1.5133376303215236,
}


def make_agent(agent_type: str, seed: int):
    """Create an agent by type string."""
    if agent_type == "evolved":
        agent = EnhancedHeuristicAgent(seed=seed)
        agent.set_weights(EVOLVED_WEIGHTS)
        return agent
    elif agent_type == "heuristic":
        return HeuristicAgent(seed=seed)
    elif agent_type == "enhanced":
        return EnhancedHeuristicAgent(seed=seed)
    elif agent_type == "random":
        return RandomAgent(seed=seed)
    raise ValueError(f"Unknown agent type: {agent_type}")


# Agent mix: varied opponents produce diverse training data
AGENT_POOL = ["evolved", "evolved", "heuristic", "enhanced", "random"]


def play_one_game(game_seed: int):
    """Play one game, recording every board state and move.

    Returns a dict with numpy arrays for all recorded data.
    """
    rng = np.random.RandomState(game_seed)

    # Pick 4 agents randomly from the pool
    agent_types = [AGENT_POOL[rng.randint(0, len(AGENT_POOL))] for _ in range(4)]
    players = list(Player)
    agents = {
        players[i]: make_agent(agent_types[i], seed=game_seed + i)
        for i in range(4)
    }

    game = BlokusGame(enable_telemetry=False)

    # Storage for this game
    boards = []
    current_players = []
    pieces_used = []
    move_counts = []
    moves_played = []

    turn = 0
    while not game.is_game_over() and turn < 2500:
        current = game.get_current_player()
        legal_moves = game.get_legal_moves(current)

        if not legal_moves:
            game.board._update_current_player()
            game._check_game_over()
            turn += 1
            continue

        # Snapshot board state BEFORE move
        boards.append(game.board.grid.copy())
        current_players.append(current.value)

        # Pieces used: 4 players × 21 pieces
        pu = np.zeros((4, 21), dtype=np.bool_)
        for i, p in enumerate(players):
            for pid in game.board.player_pieces_used[p]:
                pu[i, pid - 1] = True  # piece IDs are 1-indexed
        pieces_used.append(pu)

        move_counts.append(game.board.move_count)

        # Agent selects move
        agent = agents[current]
        move = agent.select_action(game.board, current, legal_moves)

        if move:
            moves_played.append([move.piece_id, move.orientation,
                                 move.anchor_row, move.anchor_col])
            game.make_move(move, current)
        else:
            moves_played.append([0, 0, 0, 0])
            game.board._update_current_player()
            game._check_game_over()

        turn += 1

    # Final scores
    result = game.get_game_result()
    final_scores = np.array([result.scores.get(p.value, 0) for p in players],
                            dtype=np.int16)

    if not boards:
        return None

    return {
        "boards": np.array(boards, dtype=np.int8),
        "current_players": np.array(current_players, dtype=np.int8),
        "pieces_used": np.array(pieces_used, dtype=np.bool_),
        "move_counts": np.array(move_counts, dtype=np.int16),
        "moves_played": np.array(moves_played, dtype=np.int16),
        "final_scores": final_scores,
        "agent_types": agent_types,
    }


def generate_batch(args_tuple):
    """Worker function: play a batch of games."""
    start_seed, num_games = args_tuple
    results = []
    for i in range(num_games):
        result = play_one_game(start_seed + i)
        if result is not None:
            results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description="Generate NN training data from self-play")
    parser.add_argument("--num-games", type=int, default=5000,
                        help="Number of games to play (default: 5000)")
    parser.add_argument("--workers", type=int, default=6,
                        help="Parallel workers (default: 6)")
    parser.add_argument("--output", type=str, default="data/nn_training",
                        help="Output directory (default: data/nn_training)")
    parser.add_argument("--seed", type=int, default=12345,
                        help="Base random seed (default: 12345)")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print(f"Generating {args.num_games} games with {args.workers} workers...")
    print(f"Agent pool: {AGENT_POOL}")

    t0 = time.time()

    # Split games across workers
    games_per_worker = args.num_games // args.workers
    remainder = args.num_games % args.workers
    work_items = []
    seed_offset = args.seed
    for w in range(args.workers):
        n = games_per_worker + (1 if w < remainder else 0)
        work_items.append((seed_offset, n))
        seed_offset += n

    # Run in parallel
    all_results = []
    with multiprocessing.Pool(processes=args.workers) as pool:
        for batch_results in pool.imap_unordered(generate_batch, work_items):
            all_results.extend(batch_results)
            print(f"  {len(all_results):,d}/{args.num_games} games complete...",
                  flush=True)

    elapsed = time.time() - t0
    print(f"\nPlayed {len(all_results)} games in {elapsed:.1f}s "
          f"({len(all_results)/elapsed:.1f} games/sec)")

    # Consolidate into single arrays
    all_boards = []
    all_current_players = []
    all_pieces_used = []
    all_move_counts = []
    all_moves_played = []
    all_final_scores = []
    all_game_ids = []

    for game_id, result in enumerate(all_results):
        n_states = len(result["boards"])
        all_boards.append(result["boards"])
        all_current_players.append(result["current_players"])
        all_pieces_used.append(result["pieces_used"])
        all_move_counts.append(result["move_counts"])
        all_moves_played.append(result["moves_played"])
        all_final_scores.append(result["final_scores"])
        all_game_ids.append(np.full(n_states, game_id, dtype=np.int32))

    boards = np.concatenate(all_boards)
    current_players = np.concatenate(all_current_players)
    pieces_used = np.concatenate(all_pieces_used)
    move_counts = np.concatenate(all_move_counts)
    moves_played = np.concatenate(all_moves_played)
    game_ids = np.concatenate(all_game_ids)
    final_scores = np.array(all_final_scores, dtype=np.int16)

    # Save
    output_path = os.path.join(args.output, "training_data.npz")
    np.savez_compressed(
        output_path,
        boards=boards,
        current_players=current_players,
        pieces_used=pieces_used,
        move_counts=move_counts,
        moves_played=moves_played,
        game_ids=game_ids,
        final_scores=final_scores,
    )

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nSaved {len(boards):,d} states from {len(all_results):,d} games")
    print(f"Output: {output_path} ({size_mb:.1f} MB)")
    print(f"Avg states per game: {len(boards) / len(all_results):.1f}")


if __name__ == "__main__":
    main()

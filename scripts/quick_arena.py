#!/usr/bin/env python
"""Fast head-to-head comparison without arena overhead.

Runs N games with 4 agents and reports win rates and average scores.
No telemetry, no snapshots, no rating systems — just raw results.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from agents.enhanced_heuristic_agent import EnhancedHeuristicAgent
from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from engine.board import Player
from engine.game import BlokusGame
from agents.fast_mcts_agent import FastMCTSAgent

# Load evolved weights
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

AGENT_NAMES = ["enhanced_evolved", "heuristic_default", "fast_mcts_500", "random"]


def make_agents(seed):
    evolved = EnhancedHeuristicAgent(seed=seed)
    evolved.set_weights(EVOLVED_WEIGHTS)

    default_h = HeuristicAgent(seed=seed + 1)

    # FastMCTSAgent — optimized MCTS (no board copying, cached legal moves)
    # 500 iterations with 0.5s time limit, matching repo's run_tournament.py config
    mcts = FastMCTSAgent(iterations=500, time_limit=0.5, seed=seed + 2)

    random_a = RandomAgent(seed=seed + 3)

    return [evolved, default_h, mcts, random_a]


def play_game(agents, seat_order, seed):
    """Play one game. seat_order maps Player index -> agent index."""
    game = BlokusGame(enable_telemetry=False)
    players = list(Player)

    agent_map = {}
    for i, player in enumerate(players):
        agent_map[player] = agents[seat_order[i]]

    turn = 0
    while not game.is_game_over() and turn < 2500:
        current = game.get_current_player()
        moves = game.get_legal_moves(current)
        if not moves:
            game.board._update_current_player()
            game._check_game_over()
            turn += 1
            continue
        move = agent_map[current].select_action(game.board, current, moves)
        if move:
            game.make_move(move, current)
        else:
            game.board._update_current_player()
            game._check_game_over()
        turn += 1

    result = game.get_game_result()

    # Map scores back to agent indices
    agent_scores = {}
    for i, player in enumerate(players):
        agent_idx = seat_order[i]
        score = result.scores.get(player.value, 0)
        agent_scores[agent_idx] = agent_scores.get(agent_idx, 0) + score

    # Determine winner (by agent index)
    best_score = -1
    winner_idx = -1
    for i, player in enumerate(players):
        agent_idx = seat_order[i]
        score = result.scores.get(player.value, 0)
        if score > best_score:
            best_score = score
            winner_idx = agent_idx

    return agent_scores, winner_idx


def main():
    num_games = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    seed = 42

    wins = [0] * 4
    total_scores = [0.0] * 4
    games_played = [0] * 4

    rng = np.random.RandomState(seed)
    t0 = time.time()

    print(f"Running {num_games} games: {', '.join(AGENT_NAMES)}")
    print(f"{'='*60}")

    for g in range(num_games):
        # Rotate seats each game
        seat_order = list(range(4))
        rng.shuffle(seat_order)

        agents = make_agents(seed + g * 100)
        scores, winner = play_game(agents, seat_order, seed + g)

        wins[winner] += 1
        for idx, score in scores.items():
            total_scores[idx] += score
            games_played[idx] += 1

        elapsed = time.time() - t0
        rate = (g + 1) / elapsed
        eta = (num_games - g - 1) / rate if rate > 0 else 0

        if (g + 1) % 5 == 0 or g == 0:
            print(f"  Game {g+1:3d}/{num_games} | "
                  f"{elapsed:.0f}s elapsed, ~{eta:.0f}s remaining | "
                  f"Wins: {dict(zip(AGENT_NAMES, wins))}")

    total_time = time.time() - t0

    print(f"\n{'='*60}")
    print(f" RESULTS — {num_games} games in {total_time:.1f}s")
    print(f"{'='*60}\n")

    for i, name in enumerate(AGENT_NAMES):
        avg = total_scores[i] / max(1, games_played[i])
        wr = wins[i] / num_games * 100
        print(f"  {name:25s}  Wins: {wins[i]:3d} ({wr:5.1f}%)  "
              f"Avg Score: {avg:6.1f}")

    print()


if __name__ == "__main__":
    main()

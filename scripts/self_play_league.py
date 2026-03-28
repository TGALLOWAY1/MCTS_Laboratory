#!/usr/bin/env python
"""Self-play league training with diverse opponent pool.

Instead of the NN only playing against copies of itself, it plays against
a pool of past versions (weaker selves) plus the GA-evolved agent. This
creates diverse training signal and prevents narrow strategy collapse.

Inspired by AlphaStar's league training and our island-model GA.

Usage:
    python scripts/self_play_league.py --iterations 20 --games-per-iter 40
"""

import argparse
import copy
import os
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.enhanced_heuristic_agent import EnhancedHeuristicAgent
from agents.heuristic_agent import HeuristicAgent
from agents.nn_agent import NNAgent
from agents.nn_encoding import encode_board_spatial, encode_board_scalar
from agents.nn_mcts_agent import NNMCTSAgent
from agents.nn_model import BlokusNet
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


class OpponentPool:
    """Pool of diverse opponents including past NN versions and heuristic agents."""

    def __init__(self, initial_model_path, max_past_models=5):
        self.model_paths = []  # past NN checkpoints
        self.max_past_models = max_past_models
        self.initial_model_path = initial_model_path

    def add_checkpoint(self, path):
        self.model_paths.append(path)
        # Keep only the most recent + a few historical
        if len(self.model_paths) > self.max_past_models:
            # Keep first (weakest), last few (recent), drop middle
            keep = [self.model_paths[0]] + self.model_paths[-(self.max_past_models-1):]
            self.model_paths = keep

    def sample_opponents(self, current_model_path, seed, mcts_iters=100):
        """Sample 3 diverse opponents for a 4-player game.

        Pool composition (weighted random):
          - Current NN+MCTS (self-play): 30%
          - Past NN version (weaker self): 25%
          - GA-evolved heuristic (strong baseline): 25%
          - Default heuristic (weak baseline): 10%
          - Random (floor): 10%
        """
        rng = np.random.RandomState(seed)
        opponents = []

        for i in range(3):
            roll = rng.random()
            if roll < 0.30:
                # Current model
                opponents.append(
                    NNMCTSAgent(model_path=current_model_path,
                                iterations=mcts_iters, time_limit=1.0,
                                seed=seed + i * 10))
            elif roll < 0.55 and self.model_paths:
                # Past version (random from pool)
                past_path = rng.choice(self.model_paths)
                opponents.append(
                    NNMCTSAgent(model_path=past_path,
                                iterations=mcts_iters, time_limit=1.0,
                                seed=seed + i * 10))
            elif roll < 0.80:
                # GA-evolved heuristic
                agent = EnhancedHeuristicAgent(seed=seed + i * 10)
                agent.set_weights(EVOLVED_WEIGHTS)
                opponents.append(agent)
            elif roll < 0.90:
                # Default heuristic
                opponents.append(HeuristicAgent(seed=seed + i * 10))
            else:
                # Random
                opponents.append(RandomAgent(seed=seed + i * 10))

        return opponents


def play_league_game(focal_agent, opponents, game_seed):
    """Play one game. Focal agent is the current NN being trained."""
    game = BlokusGame(enable_telemetry=False)
    players = list(Player)
    rng = np.random.RandomState(game_seed)

    # Assign focal agent to random seat
    focal_seat = rng.randint(0, 4)
    agents = {}
    opp_idx = 0
    for i, player in enumerate(players):
        if i == focal_seat:
            agents[player] = focal_agent
        else:
            agents[player] = opponents[opp_idx]
            opp_idx += 1

    focal_player = players[focal_seat]

    # Record states for focal player only
    states = []
    turn = 0

    while not game.is_game_over() and turn < 2500:
        current = game.get_current_player()
        legal_moves = game.get_legal_moves(current)

        if not legal_moves:
            game.board._update_current_player()
            game._check_game_over()
            turn += 1
            continue

        # Record state when it's the focal agent's turn
        if current == focal_player:
            spatial = encode_board_spatial(game.board.grid, current.value)
            pu = np.zeros((4, 21), dtype=bool)
            for j, p in enumerate(players):
                for pid in game.board.player_pieces_used[p]:
                    pu[j, pid - 1] = True
            scalar = encode_board_scalar(pu, game.board.move_count, current.value)
            states.append({"spatial": spatial, "scalar": scalar})

        move = agents[current].select_action(game.board, current, legal_moves)
        if move:
            game.make_move(move, current)
        else:
            game.board._update_current_player()
            game._check_game_over()
        turn += 1

    # Final score for focal player
    result = game.get_game_result()
    max_score = max(max(result.scores.values()), 1)
    focal_score = result.scores.get(focal_player.value, 0)
    focal_normalized = focal_score / max_score

    # Did the focal agent win?
    focal_won = focal_score == max(result.scores.values())

    # Backfill value targets
    training_data = []
    for state in states:
        training_data.append((
            state["spatial"],
            state["scalar"],
            focal_normalized,
        ))

    return training_data, focal_won, focal_score


def generate_league_data(current_model_path, pool, num_games,
                         mcts_iters, seed):
    """Generate training data from league play."""
    print(f"  League play: {num_games} games...", flush=True)
    t0 = time.time()

    all_spatials = []
    all_scalars = []
    all_values = []
    wins = 0
    total_score = 0

    for g in range(num_games):
        focal = NNMCTSAgent(model_path=current_model_path,
                            iterations=mcts_iters, time_limit=1.0,
                            seed=seed + g * 100)
        opponents = pool.sample_opponents(current_model_path, seed + g * 100 + 1,
                                          mcts_iters)

        data, won, score = play_league_game(focal, opponents, seed + g)

        for spatial, scalar, value in data:
            all_spatials.append(spatial)
            all_scalars.append(scalar)
            all_values.append(value)

        wins += int(won)
        total_score += score

        if (g + 1) % 10 == 0 or g == 0:
            elapsed = time.time() - t0
            rate = (g + 1) / elapsed
            eta = (num_games - g - 1) / rate
            wr = wins / (g + 1) * 100
            print(f"    Game {g+1}/{num_games} | {elapsed:.0f}s | "
                  f"~{eta:.0f}s ETA | {wr:.0f}% win | "
                  f"{len(all_spatials)} states", flush=True)

    elapsed = time.time() - t0
    wr = wins / max(num_games, 1) * 100
    avg_score = total_score / max(num_games, 1)
    print(f"  {len(all_spatials)} states, {wr:.0f}% win rate, "
          f"avg score {avg_score:.1f} ({elapsed:.0f}s)", flush=True)

    return (
        np.array(all_spatials, dtype=np.float32),
        np.array(all_scalars, dtype=np.float32),
        np.array(all_values, dtype=np.float32),
        wr,
    )


def train_on_data(model, spatials, scalars, values, epochs=5, lr=3e-4,
                  batch_size=256, device="cpu"):
    """Train value head on league data."""
    device = torch.device(device)
    model.to(device)
    model.train()

    dataset = TensorDataset(
        torch.from_numpy(spatials),
        torch.from_numpy(scalars),
        torch.from_numpy(values),
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        total_loss = 0
        n = 0
        for spatial_b, scalar_b, value_b in loader:
            spatial_b = spatial_b.to(device)
            scalar_b = scalar_b.to(device)
            value_b = value_b.to(device)

            value_pred, _ = model(spatial_b, scalar_b)
            loss = F.mse_loss(value_pred.squeeze(-1), value_b)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            n += 1

        print(f"    Epoch {epoch}: value_loss={total_loss/max(n,1):.4f}", flush=True)


def evaluate_vs_ga(model_path, num_games=10, seed=99999):
    """Evaluate NN+MCTS vs GA evolved in head-to-head games."""
    wins = {"nn": 0, "ga": 0}
    rng = np.random.RandomState(seed)

    for g in range(num_games):
        game = BlokusGame(enable_telemetry=False)
        players = list(Player)

        nn = NNMCTSAgent(model_path=model_path, iterations=500,
                         time_limit=0.5, seed=seed + g)
        ga = EnhancedHeuristicAgent(seed=seed + g + 1)
        ga.set_weights(EVOLVED_WEIGHTS)

        agents = {
            players[0]: nn if g % 2 == 0 else ga,
            players[1]: ga if g % 2 == 0 else nn,
            players[2]: RandomAgent(seed=seed + g + 2),
            players[3]: RandomAgent(seed=seed + g + 3),
        }

        turn = 0
        while not game.is_game_over() and turn < 2500:
            current = game.get_current_player()
            moves = game.get_legal_moves(current)
            if not moves:
                game.board._update_current_player()
                game._check_game_over()
                turn += 1
                continue
            move = agents[current].select_action(game.board, current, moves)
            if move:
                game.make_move(move, current)
            else:
                game.board._update_current_player()
                game._check_game_over()
            turn += 1

        result = game.get_game_result()
        nn_seat = 0 if g % 2 == 0 else 1
        ga_seat = 1 if g % 2 == 0 else 0
        if result.scores.get(players[nn_seat].value, 0) > \
           result.scores.get(players[ga_seat].value, 0):
            wins["nn"] += 1
        else:
            wins["ga"] += 1

    return wins


def main():
    parser = argparse.ArgumentParser(description="Self-play league training")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--games-per-iter", type=int, default=40)
    parser.add_argument("--mcts-iterations", type=int, default=100)
    parser.add_argument("--epochs-per-iter", type=int, default=5)
    parser.add_argument("--eval-games", type=int, default=10)
    parser.add_argument("--model", type=str, default="models/blokus_nn_v1.pt")
    parser.add_argument("--output", type=str, default="models/blokus_nn_league.pt")
    parser.add_argument("--seed", type=int, default=8888)
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f" Self-Play League Training")
    print(f" Iterations: {args.iterations}")
    print(f" Games/iter: {args.games_per_iter}")
    print(f" MCTS iters/move: {args.mcts_iterations}")
    print(f" Opponent pool: current NN + past versions + GA + heuristic + random")
    print(f" Starting model: {args.model}")
    print(f"{'='*60}\n")

    model = BlokusNet()
    checkpoint = torch.load(args.model, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])

    pool = OpponentPool(args.model)
    current_model_path = args.model
    best_win_rate = 0.0

    t_total = time.time()

    for iteration in range(args.iterations):
        print(f"\n{'─'*60}")
        print(f" Iteration {iteration + 1}/{args.iterations} "
              f"(pool: {len(pool.model_paths)} past models)")
        print(f"{'─'*60}", flush=True)

        iter_seed = args.seed + iteration * 10000

        # 1. Generate league data
        spatials, scalars, values, league_wr = generate_league_data(
            current_model_path, pool, args.games_per_iter,
            args.mcts_iterations, iter_seed)

        # 2. Train
        print(f"  Training ({len(spatials)} states)...", flush=True)
        train_on_data(model, spatials, scalars, values,
                      epochs=args.epochs_per_iter)

        # 3. Save checkpoint and add to pool
        iter_path = args.output.replace(".pt", f"_iter{iteration+1}.pt")
        os.makedirs(os.path.dirname(iter_path) or ".", exist_ok=True)
        torch.save({"model_state_dict": model.state_dict(),
                     "iteration": iteration + 1}, iter_path)
        pool.add_checkpoint(iter_path)
        current_model_path = iter_path

        # 4. Evaluate vs GA
        print(f"  Evaluating vs GA ({args.eval_games} games)...", flush=True)
        wins = evaluate_vs_ga(current_model_path, args.eval_games,
                              seed=iter_seed + 5000)
        nn_wr = wins["nn"] / max(1, sum(wins.values())) * 100
        print(f"  >> NN+MCTS {wins['nn']} — GA {wins['ga']} "
              f"({nn_wr:.0f}% NN win rate)", flush=True)

        if nn_wr > best_win_rate:
            best_win_rate = nn_wr
            torch.save({"model_state_dict": model.state_dict(),
                         "iteration": iteration + 1,
                         "win_rate_vs_ga": nn_wr}, args.output)
            print(f"  ** New best! Saved to {args.output}", flush=True)

    total_time = time.time() - t_total
    print(f"\n{'='*60}")
    print(f" League training complete in {total_time/60:.0f} min")
    print(f" Best NN win rate vs GA: {best_win_rate:.0f}%")
    print(f" Best model: {args.output}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

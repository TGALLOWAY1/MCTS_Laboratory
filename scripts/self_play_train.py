#!/usr/bin/env python
"""Stage 2: Self-play reinforcement learning for the Blokus NN.

The NN+MCTS plays games against itself, generating training data that's
higher quality than the supervised pre-training data. Each iteration:
  1. Play N games using NN+MCTS (4 copies, one per player)
  2. Record board states and final scores
  3. Retrain the NN on the new data
  4. Repeat — each cycle produces better data and a better NN

Usage:
    python scripts/self_play_train.py --iterations 10 --games-per-iter 50
    python scripts/self_play_train.py --iterations 5 --games-per-iter 20 --quick
"""

import argparse
import os
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.nn_encoding import encode_board_spatial, encode_board_scalar
from agents.nn_model import BlokusNet
from agents.nn_mcts_agent import NNMCTSAgent
from engine.board import Player
from engine.game import BlokusGame


def play_self_play_game(agents, game_seed):
    """Play one self-play game, recording every board state.

    Returns list of (spatial, scalar, value_target) tuples.
    """
    game = BlokusGame(enable_telemetry=False)
    players = list(Player)

    # Shuffle seat assignments
    rng = np.random.RandomState(game_seed)
    seat_order = list(range(4))
    rng.shuffle(seat_order)

    agent_map = {players[i]: agents[seat_order[i]] for i in range(4)}

    # Record states
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

        # Record board state BEFORE move
        spatial = encode_board_spatial(game.board.grid, current.value)
        pu = np.zeros((4, 21), dtype=bool)
        for i, p in enumerate(players):
            for pid in game.board.player_pieces_used[p]:
                pu[i, pid - 1] = True
        scalar = encode_board_scalar(pu, game.board.move_count, current.value)

        states.append({
            "spatial": spatial,
            "scalar": scalar,
            "player_idx": current.value - 1,
        })

        # Play move
        agent = agent_map[current]
        move = agent.select_action(game.board, current, legal_moves)
        if move:
            game.make_move(move, current)
        else:
            game.board._update_current_player()
            game._check_game_over()
        turn += 1

    # Get final scores and normalize
    result = game.get_game_result()
    max_score = max(result.scores.values()) if result.scores else 1
    max_score = max(max_score, 1)

    # Backfill value targets
    training_data = []
    for state in states:
        player_idx = state["player_idx"]
        score = result.scores.get(player_idx + 1, 0)
        value_target = score / max_score
        training_data.append((
            state["spatial"],
            state["scalar"],
            value_target,
        ))

    return training_data


def generate_self_play_data(model_path, num_games, mcts_iterations, seed):
    """Generate training data from NN+MCTS self-play."""
    print(f"  Generating {num_games} self-play games...", flush=True)
    t0 = time.time()

    all_spatials = []
    all_scalars = []
    all_values = []

    for g in range(num_games):
        # Create 4 copies of NN+MCTS agent
        agents = [
            NNMCTSAgent(model_path=model_path, iterations=mcts_iterations,
                        time_limit=1.0, seed=seed + g * 10 + i)
            for i in range(4)
        ]

        data = play_self_play_game(agents, seed + g)

        for spatial, scalar, value in data:
            all_spatials.append(spatial)
            all_scalars.append(scalar)
            all_values.append(value)

        if (g + 1) % 10 == 0 or g == 0:
            elapsed = time.time() - t0
            rate = (g + 1) / elapsed
            eta = (num_games - g - 1) / rate
            print(f"    Game {g+1}/{num_games} | {elapsed:.0f}s | "
                  f"~{eta:.0f}s remaining | {len(all_spatials)} states",
                  flush=True)

    elapsed = time.time() - t0
    print(f"  Generated {len(all_spatials)} states from {num_games} games "
          f"in {elapsed:.0f}s", flush=True)

    return (
        np.array(all_spatials, dtype=np.float32),
        np.array(all_scalars, dtype=np.float32),
        np.array(all_values, dtype=np.float32),
    )


def train_on_data(model, spatials, scalars, values, epochs=5, lr=5e-4,
                  batch_size=256, device="cpu"):
    """Train the model on self-play data (value head only)."""
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

        avg_loss = total_loss / max(n, 1)
        print(f"    Epoch {epoch}: value_loss={avg_loss:.4f}", flush=True)

    return avg_loss


def evaluate_against_ga(model_path, num_games=10, seed=99999):
    """Quick evaluation: NN+MCTS vs GA evolved."""
    from agents.enhanced_heuristic_agent import EnhancedHeuristicAgent

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

    wins = {"nn_mcts": 0, "ga_evolved": 0}
    rng = np.random.RandomState(seed)

    for g in range(num_games):
        game = BlokusGame(enable_telemetry=False)
        players = list(Player)

        nn_agent = NNMCTSAgent(model_path=model_path, iterations=500,
                               time_limit=0.5, seed=seed + g)
        ga_agent = EnhancedHeuristicAgent(seed=seed + g + 1)
        ga_agent.set_weights(EVOLVED_WEIGHTS)

        # Alternate who gets seats 0,1 vs 2,3
        from agents.random_agent import RandomAgent
        agents = {
            players[0]: nn_agent if g % 2 == 0 else ga_agent,
            players[1]: ga_agent if g % 2 == 0 else nn_agent,
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
        nn_score = result.scores.get(players[nn_seat].value, 0)
        ga_score = result.scores.get(players[ga_seat].value, 0)

        if nn_score > ga_score:
            wins["nn_mcts"] += 1
        else:
            wins["ga_evolved"] += 1

    return wins


def main():
    parser = argparse.ArgumentParser(description="Self-play RL training loop")
    parser.add_argument("--iterations", type=int, default=10,
                        help="Number of self-play iterations (default: 10)")
    parser.add_argument("--games-per-iter", type=int, default=50,
                        help="Games per iteration (default: 50)")
    parser.add_argument("--mcts-iterations", type=int, default=100,
                        help="MCTS iterations per move during self-play (default: 100)")
    parser.add_argument("--epochs-per-iter", type=int, default=5,
                        help="Training epochs per iteration (default: 5)")
    parser.add_argument("--eval-games", type=int, default=10,
                        help="Evaluation games vs GA after each iteration (default: 10)")
    parser.add_argument("--model", type=str, default="models/blokus_nn_v1.pt",
                        help="Starting model checkpoint")
    parser.add_argument("--output", type=str, default="models/blokus_nn_selfplay.pt",
                        help="Output model path")
    parser.add_argument("--seed", type=int, default=7777)
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: fewer games and iterations")
    args = parser.parse_args()

    if args.quick:
        args.games_per_iter = min(args.games_per_iter, 10)
        args.mcts_iterations = min(args.mcts_iterations, 50)
        args.eval_games = min(args.eval_games, 5)
        args.epochs_per_iter = min(args.epochs_per_iter, 3)

    print(f"{'='*60}")
    print(f" Self-Play RL Training")
    print(f" Iterations: {args.iterations}")
    print(f" Games/iter: {args.games_per_iter}")
    print(f" MCTS iterations/move: {args.mcts_iterations}")
    print(f" Starting model: {args.model}")
    print(f"{'='*60}\n")

    # Load model
    model = BlokusNet()
    checkpoint = torch.load(args.model, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])

    current_model_path = args.model
    best_win_rate = 0.0

    t_total = time.time()

    for iteration in range(args.iterations):
        print(f"\n--- Iteration {iteration + 1}/{args.iterations} ---", flush=True)
        iter_seed = args.seed + iteration * 10000

        # 1. Generate self-play data
        spatials, scalars, values = generate_self_play_data(
            current_model_path, args.games_per_iter,
            args.mcts_iterations, iter_seed)

        # 2. Train on self-play data
        print(f"  Training ({len(spatials)} states, {args.epochs_per_iter} epochs)...",
              flush=True)
        loss = train_on_data(model, spatials, scalars, values,
                             epochs=args.epochs_per_iter)

        # 3. Save checkpoint
        iter_path = args.output.replace(".pt", f"_iter{iteration+1}.pt")
        os.makedirs(os.path.dirname(iter_path) or ".", exist_ok=True)
        torch.save({"model_state_dict": model.state_dict(),
                     "iteration": iteration + 1,
                     "value_loss": loss}, iter_path)
        current_model_path = iter_path

        # 4. Evaluate vs GA
        print(f"  Evaluating vs GA evolved ({args.eval_games} games)...", flush=True)
        wins = evaluate_against_ga(current_model_path, args.eval_games,
                                   seed=iter_seed + 5000)
        nn_wr = wins["nn_mcts"] / max(1, sum(wins.values())) * 100
        print(f"  NN+MCTS: {wins['nn_mcts']} wins, "
              f"GA: {wins['ga_evolved']} wins ({nn_wr:.0f}% NN win rate)",
              flush=True)

        if nn_wr > best_win_rate:
            best_win_rate = nn_wr
            torch.save({"model_state_dict": model.state_dict(),
                         "iteration": iteration + 1,
                         "win_rate_vs_ga": nn_wr}, args.output)
            print(f"  New best! Saved to {args.output}", flush=True)

    total_time = time.time() - t_total
    print(f"\n{'='*60}")
    print(f" Self-play complete in {total_time:.0f}s")
    print(f" Best NN win rate vs GA: {best_win_rate:.0f}%")
    print(f" Best model: {args.output}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Train Blokus neural network from self-play data.

Usage:
    python scripts/train_nn.py --data data/nn_training/training_data.npz
    python scripts/train_nn.py --data data/nn_training/training_data.npz --epochs 30 --batch-size 256
"""

import argparse
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.nn_model import BlokusNet
from agents.nn_encoding import (
    encode_board_spatial, encode_board_scalar,
    NUM_SPATIAL_CHANNELS, NUM_SCALAR_FEATURES,
)


class BlokusDataset(Dataset):
    """Dataset of Blokus board states with value and policy targets."""

    def __init__(self, data_path: str, max_negatives: int = 15):
        print(f"Loading data from {data_path}...")
        data = np.load(data_path)

        self.boards = data["boards"]           # (N, 20, 20) int8
        self.current_players = data["current_players"]  # (N,) int8
        self.pieces_used = data["pieces_used"]  # (N, 4, 21) bool
        self.move_counts = data["move_counts"]  # (N,) int16
        self.moves_played = data["moves_played"]  # (N, 4) int16
        self.game_ids = data["game_ids"]        # (N,) int32
        self.final_scores = data["final_scores"]  # (G, 4) int16

        self.max_negatives = max_negatives
        self.n_states = len(self.boards)
        self.rng = np.random.RandomState(42)

        # Precompute max score for normalization
        self.max_score = max(float(self.final_scores.max()), 1.0)

        print(f"  {self.n_states:,d} states from {len(self.final_scores):,d} games")
        print(f"  Max score: {self.max_score}")

    def __len__(self):
        return self.n_states

    def __getitem__(self, idx):
        board = self.boards[idx]
        cp = int(self.current_players[idx])
        pu = self.pieces_used[idx]
        mc = int(self.move_counts[idx])
        move = self.moves_played[idx]
        game_id = int(self.game_ids[idx])

        # Encode inputs
        spatial = encode_board_spatial(board, cp)
        scalar = encode_board_scalar(pu, mc, cp)

        # Value target: normalized final score for current player
        # Rotate so current player maps to index 0
        player_idx = cp - 1  # 0-indexed
        score = float(self.final_scores[game_id, player_idx])
        value_target = score / self.max_score

        # Policy: positive move + random negatives
        K = 1 + self.max_negatives
        candidates = np.zeros((K, 4), dtype=np.int16)
        mask = np.zeros(K, dtype=np.bool_)

        # Positive: the move actually played
        candidates[0] = move
        mask[0] = True

        # Negatives: random (piece_id, orientation, row, col) tuples
        for i in range(1, K):
            candidates[i] = [
                self.rng.randint(1, 22),   # piece_id 1-21
                self.rng.randint(0, 8),    # orientation 0-7
                self.rng.randint(0, 20),   # anchor_row
                self.rng.randint(0, 20),   # anchor_col
            ]
            mask[i] = True

        return {
            "spatial": torch.from_numpy(spatial),
            "scalar": torch.from_numpy(scalar),
            "value_target": torch.tensor(value_target, dtype=torch.float32),
            "candidates": torch.from_numpy(candidates.astype(np.int64)),
            "mask": torch.from_numpy(mask),
            "policy_target": torch.tensor(0, dtype=torch.long),  # index 0 is the positive
        }


def train_epoch(model, loader, optimizer, device, epoch):
    model.train()
    total_value_loss = 0.0
    total_policy_loss = 0.0
    total_loss = 0.0
    n_batches = 0

    for batch in loader:
        spatial = batch["spatial"].to(device)
        scalar = batch["scalar"].to(device)
        value_target = batch["value_target"].to(device)
        candidates = batch["candidates"].to(device)
        mask = batch["mask"].to(device)
        policy_target = batch["policy_target"].to(device)

        # Forward
        value_pred, features = model(spatial, scalar)

        # Value loss
        value_loss = F.mse_loss(value_pred.squeeze(-1), value_target)

        # Policy loss: score candidates, cross-entropy with target=0 (positive)
        move_logits = model.policy_score_moves(features, scalar, candidates, mask)
        policy_loss = F.cross_entropy(move_logits, policy_target)

        loss = value_loss + policy_loss

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_value_loss += value_loss.item()
        total_policy_loss += policy_loss.item()
        total_loss += loss.item()
        n_batches += 1

    return {
        "loss": total_loss / n_batches,
        "value_loss": total_value_loss / n_batches,
        "policy_loss": total_policy_loss / n_batches,
    }


@torch.no_grad()
def eval_epoch(model, loader, device):
    model.eval()
    total_value_loss = 0.0
    total_policy_loss = 0.0
    total_policy_acc = 0.0
    n_batches = 0

    for batch in loader:
        spatial = batch["spatial"].to(device)
        scalar = batch["scalar"].to(device)
        value_target = batch["value_target"].to(device)
        candidates = batch["candidates"].to(device)
        mask = batch["mask"].to(device)
        policy_target = batch["policy_target"].to(device)

        value_pred, features = model(spatial, scalar)
        value_loss = F.mse_loss(value_pred.squeeze(-1), value_target)

        move_logits = model.policy_score_moves(features, scalar, candidates, mask)
        policy_loss = F.cross_entropy(move_logits, policy_target)

        # Policy accuracy: does the model rank the positive move highest?
        predicted = move_logits.argmax(dim=1)
        acc = (predicted == policy_target).float().mean()

        total_value_loss += value_loss.item()
        total_policy_loss += policy_loss.item()
        total_policy_acc += acc.item()
        n_batches += 1

    return {
        "value_loss": total_value_loss / n_batches,
        "policy_loss": total_policy_loss / n_batches,
        "policy_acc": total_policy_acc / n_batches,
    }


def main():
    parser = argparse.ArgumentParser(description="Train Blokus neural network")
    parser.add_argument("--data", type=str, default="data/nn_training/training_data.npz")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-split", type=float, default=0.15,
                        help="Validation split by game (default: 0.15)")
    parser.add_argument("--output", type=str, default="models/blokus_nn_v1.pt")
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    device = torch.device(args.device)

    # Load dataset
    full_dataset = BlokusDataset(args.data)

    # Split by game_id to prevent data leakage
    game_ids = full_dataset.game_ids
    unique_games = np.unique(game_ids)
    rng = np.random.RandomState(42)
    rng.shuffle(unique_games)

    n_val_games = max(1, int(len(unique_games) * args.val_split))
    val_games = set(unique_games[:n_val_games])

    val_indices = [i for i in range(len(full_dataset)) if game_ids[i] in val_games]
    train_indices = [i for i in range(len(full_dataset)) if game_ids[i] not in val_games]

    train_dataset = torch.utils.data.Subset(full_dataset, train_indices)
    val_dataset = torch.utils.data.Subset(full_dataset, val_indices)

    print(f"  Train: {len(train_dataset):,d} states, Val: {len(val_dataset):,d} states")

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size,
                              shuffle=True, num_workers=0, pin_memory=False)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size,
                            shuffle=False, num_workers=0, pin_memory=False)

    # Model
    model = BlokusNet().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"\nBlokusNet: {n_params:,d} parameters")

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    # Training loop
    best_val_loss = float("inf")
    best_epoch = 0

    print(f"\nTraining for {args.epochs} epochs on {device}...")
    print(f"{'Epoch':>5} | {'Train Loss':>10} | {'Val Loss':>10} | "
          f"{'V-Loss':>7} | {'P-Loss':>7} | {'P-Acc':>7} | {'LR':>8} | {'Time':>5}")
    print("-" * 80)

    t_start = time.time()

    for epoch in range(args.epochs):
        t0 = time.time()

        train_metrics = train_epoch(model, train_loader, optimizer, device, epoch)
        val_metrics = eval_epoch(model, val_loader, device)

        scheduler.step()
        lr = scheduler.get_last_lr()[0]
        elapsed = time.time() - t0

        val_loss = val_metrics["value_loss"] + val_metrics["policy_loss"]

        print(f"{epoch:5d} | {train_metrics['loss']:10.4f} | {val_loss:10.4f} | "
              f"{val_metrics['value_loss']:7.4f} | {val_metrics['policy_loss']:7.4f} | "
              f"{val_metrics['policy_acc']:7.1%} | {lr:8.6f} | {elapsed:5.1f}s",
              flush=True)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "epoch": epoch,
                "val_loss": val_loss,
                "val_metrics": val_metrics,
                "n_params": n_params,
            }, args.output)

    total_time = time.time() - t_start

    print(f"\n{'='*80}")
    print(f"Training complete in {total_time:.1f}s")
    print(f"Best epoch: {best_epoch}, best val loss: {best_val_loss:.4f}")
    print(f"Model saved to {args.output}")

    # Load best and report final metrics
    checkpoint = torch.load(args.output, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    final_val = eval_epoch(model, val_loader, device)
    print(f"Final val — value_loss: {final_val['value_loss']:.4f}, "
          f"policy_loss: {final_val['policy_loss']:.4f}, "
          f"policy_acc: {final_val['policy_acc']:.1%}")


if __name__ == "__main__":
    main()

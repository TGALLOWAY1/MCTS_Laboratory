#!/usr/bin/env python
"""Train a pairwise win-probability model from self-play snapshots.

Supports two model types matching ``mcts/learned_evaluator.py``'s artifact
format:

  - ``pairwise_logreg``  — StandardScaler + LogisticRegression pipeline
  - ``pairwise_gbt_phase`` — Per-phase GBT models + fallback

Example
-------
python scripts/train_eval_model.py \
    --data data/snapshots.parquet \
    --model-type pairwise_gbt_phase \
    --output models/eval_v1.pkl \
    --test-size 0.2 \
    --seed 42
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from analytics.winprob.dataset import (
    build_pairwise_dataset,
    load_snapshots_dataframe,
    split_pairwise_by_game,
)
from analytics.winprob.features import SNAPSHOT_FEATURE_COLUMNS


# ---------------------------------------------------------------------------
# Model trainers
# ---------------------------------------------------------------------------

def _train_logreg(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: list[str],
    seed: int,
) -> Dict[str, Any]:
    """Train a logistic regression pairwise model."""
    X_train = train_df[feature_columns].values
    y_train = train_df["label"].values
    X_test = test_df[feature_columns].values
    y_test = test_df["label"].values

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("logreg", LogisticRegression(max_iter=2000, random_state=seed, solver="lbfgs")),
    ])
    pipeline.fit(X_train, y_train)

    # Evaluate
    metrics = _evaluate(pipeline, X_train, y_train, X_test, y_test)

    artifact = {
        "model_type": "pairwise_logreg",
        "feature_columns": list(feature_columns),
        "pipeline": pipeline,
    }
    return artifact, metrics


def _train_gbt_phase(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: list[str],
    seed: int,
) -> Dict[str, Any]:
    """Train per-phase GBT models + fallback."""
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier as GBT
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier as GBT

    phase_models: Dict[str, Any] = {}
    phase_metrics: Dict[str, Dict] = {}

    for phase in ["early", "mid", "late"]:
        phase_train = train_df[train_df["phase_bucket"] == phase]
        phase_test = test_df[test_df["phase_bucket"] == phase]

        if len(phase_train) < 20:
            print(f"  WARNING: Phase '{phase}' has only {len(phase_train)} training rows — skipping dedicated model.")
            continue

        X_tr = phase_train[feature_columns].values
        y_tr = phase_train["label"].values

        model = Pipeline([
            ("scaler", StandardScaler()),
            ("gbt", GBT(max_iter=300, learning_rate=0.1, max_depth=5, random_state=seed)),
        ])
        model.fit(X_tr, y_tr)
        phase_models[phase] = model

        if len(phase_test) >= 5:
            X_te = phase_test[feature_columns].values
            y_te = phase_test["label"].values
            phase_metrics[phase] = _evaluate(model, X_tr, y_tr, X_te, y_te)
            print(f"  Phase '{phase}': train_acc={phase_metrics[phase]['train_accuracy']:.4f}  "
                  f"test_acc={phase_metrics[phase]['test_accuracy']:.4f}  "
                  f"test_logloss={phase_metrics[phase]['test_logloss']:.4f}")

    # Fallback model on all data
    X_train_all = train_df[feature_columns].values
    y_train_all = train_df["label"].values
    X_test_all = test_df[feature_columns].values
    y_test_all = test_df["label"].values

    fallback = Pipeline([
        ("scaler", StandardScaler()),
        ("gbt", GBT(max_iter=300, learning_rate=0.1, max_depth=5, random_state=seed)),
    ])
    fallback.fit(X_train_all, y_train_all)

    metrics = _evaluate(fallback, X_train_all, y_train_all, X_test_all, y_test_all)
    metrics["phase_metrics"] = phase_metrics

    artifact = {
        "model_type": "pairwise_gbt_phase",
        "feature_columns": list(feature_columns),
        "phase_models": phase_models,
        "fallback_model": fallback,
    }
    return artifact, metrics


def _evaluate(model, X_train, y_train, X_test, y_test) -> Dict[str, Any]:
    """Compute train/test accuracy, log-loss, and calibration stats."""
    train_pred = model.predict_proba(X_train)[:, 1]
    test_pred = model.predict_proba(X_test)[:, 1]

    train_acc = accuracy_score(y_train, (train_pred >= 0.5).astype(int))
    test_acc = accuracy_score(y_test, (test_pred >= 0.5).astype(int))
    train_ll = log_loss(y_train, train_pred)
    test_ll = log_loss(y_test, test_pred)

    # Calibration (5 bins)
    try:
        fraction_pos, mean_predicted = calibration_curve(y_test, test_pred, n_bins=5, strategy="uniform")
        cal_error = float(np.mean(np.abs(fraction_pos - mean_predicted)))
    except Exception:
        cal_error = float("nan")

    return {
        "train_accuracy": float(train_acc),
        "test_accuracy": float(test_acc),
        "train_logloss": float(train_ll),
        "test_logloss": float(test_ll),
        "calibration_error": cal_error,
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train pairwise win-probability model.")
    parser.add_argument("--data", type=str, required=True, help="Path to snapshots parquet/csv.")
    parser.add_argument(
        "--model-type",
        type=str,
        default="pairwise_gbt_phase",
        choices=["pairwise_logreg", "pairwise_gbt_phase"],
        help="Model type to train.",
    )
    parser.add_argument("--output", type=str, default="models/eval_v1.pkl", help="Output artifact path.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction of games for test set.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    t0 = time.time()

    print(f"=== Model Training ===")
    print(f"  data:       {args.data}")
    print(f"  model_type: {args.model_type}")
    print(f"  output:     {args.output}")
    print(f"  test_size:  {args.test_size}")
    print(f"  seed:       {args.seed}")
    print()

    # 1. Load snapshots
    print("Loading snapshots...")
    snapshots_df = load_snapshots_dataframe(args.data)
    print(f"  {len(snapshots_df)} snapshot rows, {snapshots_df['game_id'].nunique()} games")

    # 2. Build pairwise dataset
    print("Building pairwise dataset...")
    pairwise_df, pw_meta = build_pairwise_dataset(snapshots_df)
    print(f"  {pw_meta['rows']} pairwise rows, {pw_meta['ties_dropped']} ties dropped")

    if pairwise_df.empty:
        print("ERROR: No pairwise rows generated. Check input data.")
        return

    # 3. Split
    print("Splitting by game...")
    train_df, test_df, split_meta = split_pairwise_by_game(
        pairwise_df, test_size=args.test_size, seed=args.seed
    )
    print(f"  train: {split_meta['train_rows']} rows ({split_meta['train_games']} games)")
    print(f"  test:  {split_meta['test_rows']} rows ({split_meta['test_games']} games)")

    # 4. Train
    feature_columns = list(SNAPSHOT_FEATURE_COLUMNS)
    print(f"\nTraining {args.model_type}...")

    if args.model_type == "pairwise_logreg":
        artifact, metrics = _train_logreg(train_df, test_df, feature_columns, args.seed)
    elif args.model_type == "pairwise_gbt_phase":
        artifact, metrics = _train_gbt_phase(train_df, test_df, feature_columns, args.seed)
    else:
        raise ValueError(f"Unknown model type: {args.model_type}")

    # 5. Report
    print(f"\n=== Results ===")
    print(f"  Train accuracy:    {metrics['train_accuracy']:.4f}")
    print(f"  Test accuracy:     {metrics['test_accuracy']:.4f}")
    print(f"  Train log-loss:    {metrics['train_logloss']:.4f}")
    print(f"  Test log-loss:     {metrics['test_logloss']:.4f}")
    print(f"  Calibration error: {metrics['calibration_error']:.4f}")

    # 6. Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, str(output_path))

    elapsed = time.time() - t0
    print(f"\n  Artifact saved to: {output_path}")
    print(f"  Artifact keys:     {sorted(artifact.keys())}")
    print(f"  Time elapsed:      {elapsed:.1f}s")


if __name__ == "__main__":
    main()

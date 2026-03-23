#!/usr/bin/env python
"""Layer 6.1 — Feature importance analysis via regression and SHAP.

Reads the self-play parquet produced by ``collect_layer6_data.py`` and runs:

1. **Linear Regression** on both the 7 state-evaluator features and the full
   35-feature winprob set.  Reports R^2, coefficients, and bootstrap CIs.
2. **Random Forest Regression** with SHAP analysis (Soemers methodology).
3. **Residual Analysis** — residuals plotted against turn number, board
   occupancy, and score difference.
4. **Per-phase regressions** (early / mid / late) to produce phase-dependent
   weight vectors for ``BlokusStateEvaluator``.

Outputs:
- ``data/layer6_analysis_results.json`` — R^2, coefficients, phase weights
- ``data/layer6_plots/`` — PNG plots for residuals, SHAP, feature importance
- ``data/layer6_calibrated_weights.json`` — optimised single + phase weights
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

warnings.filterwarnings("ignore", category=FutureWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score

from mcts.state_evaluator import (
    DEFAULT_WEIGHTS,
    FEATURE_NAMES,
    PHASE_EARLY_THRESHOLD,
    PHASE_LATE_THRESHOLD,
)

SE_PREFIX = "se_"
SE_FEATURE_COLS = [SE_PREFIX + f for f in FEATURE_NAMES]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bootstrap_coefs(
    X: np.ndarray, y: np.ndarray, n_boot: int = 1000, seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (lower_ci, upper_ci) for linear regression coefficients."""
    rng = np.random.RandomState(seed)
    n = len(y)
    coefs = np.zeros((n_boot, X.shape[1]))
    for i in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        lr = LinearRegression().fit(X[idx], y[idx])
        coefs[i] = lr.coef_
    lo = np.percentile(coefs, 2.5, axis=0)
    hi = np.percentile(coefs, 97.5, axis=0)
    return lo, hi


def _run_linear_regression(
    df: pd.DataFrame,
    feature_cols: List[str],
    label: str,
) -> Dict[str, Any]:
    """Fit linear regression, return results dict."""
    X = df[feature_cols].values.astype(float)
    y = df[label].values.astype(float)

    lr = LinearRegression().fit(X, y)
    r2 = lr.score(X, y)

    # Cross-validated R^2
    cv_scores = cross_val_score(lr, X, y, cv=5, scoring="r2")

    lo, hi = _bootstrap_coefs(X, y)
    coef_table = []
    for i, col in enumerate(feature_cols):
        significant = not (lo[i] <= 0 <= hi[i])
        coef_table.append({
            "feature": col,
            "coefficient": float(lr.coef_[i]),
            "ci_lower": float(lo[i]),
            "ci_upper": float(hi[i]),
            "significant": significant,
        })

    # Sort by absolute coefficient
    coef_table.sort(key=lambda x: abs(x["coefficient"]), reverse=True)

    residuals = y - lr.predict(X)

    return {
        "r2": float(r2),
        "r2_cv_mean": float(np.mean(cv_scores)),
        "r2_cv_std": float(np.std(cv_scores)),
        "intercept": float(lr.intercept_),
        "coefficients": coef_table,
        "residuals": residuals,
        "predictions": lr.predict(X),
    }


def _run_random_forest(
    df: pd.DataFrame,
    feature_cols: List[str],
    label: str,
) -> Dict[str, Any]:
    """Fit Random Forest, return results + SHAP values if available."""
    X = df[feature_cols].values.astype(float)
    y = df[label].values.astype(float)

    rf = RandomForestRegressor(
        n_estimators=200, max_depth=12, min_samples_leaf=10,
        random_state=42, n_jobs=-1,
    )
    rf.fit(X, y)
    r2 = rf.score(X, y)
    cv_scores = cross_val_score(rf, X, y, cv=5, scoring="r2")

    # Feature importances (MDI)
    importances = rf.feature_importances_
    importance_table = sorted(
        [{"feature": col, "importance": float(imp)}
         for col, imp in zip(feature_cols, importances)],
        key=lambda x: x["importance"], reverse=True,
    )

    result: Dict[str, Any] = {
        "r2": float(r2),
        "r2_cv_mean": float(np.mean(cv_scores)),
        "r2_cv_std": float(np.std(cv_scores)),
        "importances": importance_table,
    }

    # SHAP analysis (optional)
    try:
        import shap
        explainer = shap.TreeExplainer(rf)
        # Use a subsample for speed
        sample_size = min(2000, len(X))
        rng = np.random.RandomState(42)
        idx = rng.choice(len(X), size=sample_size, replace=False)
        shap_values = explainer.shap_values(X[idx])

        mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
        shap_table = sorted(
            [{"feature": col, "mean_abs_shap": float(val)}
             for col, val in zip(feature_cols, mean_abs_shap)],
            key=lambda x: x["mean_abs_shap"], reverse=True,
        )
        result["shap_importances"] = shap_table
        result["shap_values"] = shap_values
        result["shap_sample_idx"] = idx
    except ImportError:
        print("  [WARN] shap not installed — skipping SHAP analysis")
        result["shap_importances"] = None

    return result


def _residual_analysis(
    df: pd.DataFrame,
    residuals: np.ndarray,
    predictions: np.ndarray,
    plot_dir: Path,
) -> Dict[str, Any]:
    """Compute and plot residual diagnostics."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        has_mpl = True
    except ImportError:
        has_mpl = False
        print("  [WARN] matplotlib not installed — skipping plots")

    y = df["final_score"].values.astype(float)
    turn = df["turn_index"].values.astype(float) if "turn_index" in df.columns else None
    occ = df["phase_board_occupancy"].values.astype(float)
    score_diff = y - np.mean(y)

    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mae = float(np.mean(np.abs(residuals)))

    # Residual stats by phase
    phase_stats = {}
    for label, mask in [
        ("early", occ < PHASE_EARLY_THRESHOLD),
        ("mid", (occ >= PHASE_EARLY_THRESHOLD) & (occ < PHASE_LATE_THRESHOLD)),
        ("late", occ >= PHASE_LATE_THRESHOLD),
    ]:
        if mask.sum() > 0:
            phase_stats[label] = {
                "count": int(mask.sum()),
                "rmse": float(np.sqrt(np.mean(residuals[mask] ** 2))),
                "mae": float(np.mean(np.abs(residuals[mask]))),
                "mean_residual": float(np.mean(residuals[mask])),
            }

    result = {
        "rmse": rmse,
        "mae": mae,
        "phase_residual_stats": phase_stats,
    }

    if has_mpl:
        plot_dir.mkdir(parents=True, exist_ok=True)

        # 1. Residuals vs board occupancy
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(occ, residuals, alpha=0.15, s=8)
        ax.axhline(0, color="red", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Board Occupancy")
        ax.set_ylabel("Residual (actual - predicted)")
        ax.set_title("Residuals vs Board Occupancy")
        fig.tight_layout()
        fig.savefig(str(plot_dir / "residuals_vs_occupancy.png"), dpi=150)
        plt.close(fig)

        # 2. Residuals vs turn index
        if turn is not None:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.scatter(turn, residuals, alpha=0.15, s=8)
            ax.axhline(0, color="red", linestyle="--", linewidth=0.8)
            ax.set_xlabel("Turn Index")
            ax.set_ylabel("Residual")
            ax.set_title("Residuals vs Turn Index")
            fig.tight_layout()
            fig.savefig(str(plot_dir / "residuals_vs_turn.png"), dpi=150)
            plt.close(fig)

        # 3. Residuals vs score difference
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(score_diff, residuals, alpha=0.15, s=8)
        ax.axhline(0, color="red", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Score Difference (from mean)")
        ax.set_ylabel("Residual")
        ax.set_title("Residuals vs Score Difference")
        fig.tight_layout()
        fig.savefig(str(plot_dir / "residuals_vs_score_diff.png"), dpi=150)
        plt.close(fig)

        # 4. Predicted vs actual
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.scatter(predictions, y, alpha=0.15, s=8)
        mn, mx = min(predictions.min(), y.min()), max(predictions.max(), y.max())
        ax.plot([mn, mx], [mn, mx], "r--", linewidth=0.8)
        ax.set_xlabel("Predicted Score")
        ax.set_ylabel("Actual Score")
        ax.set_title("Predicted vs Actual Final Score")
        fig.tight_layout()
        fig.savefig(str(plot_dir / "predicted_vs_actual.png"), dpi=150)
        plt.close(fig)

        print(f"  Plots saved to {plot_dir}/")

    return result


def _derive_phase_weights(
    df: pd.DataFrame,
) -> Dict[str, Dict[str, float]]:
    """Run per-phase linear regressions on the 7 state-evaluator features
    and return normalised weight dicts for each phase."""
    occ = df["phase_board_occupancy"]
    phases = {
        "early": df[occ < PHASE_EARLY_THRESHOLD],
        "mid": df[(occ >= PHASE_EARLY_THRESHOLD) & (occ < PHASE_LATE_THRESHOLD)],
        "late": df[occ >= PHASE_LATE_THRESHOLD],
    }

    phase_weights: Dict[str, Dict[str, float]] = {}
    phase_r2: Dict[str, float] = {}

    for phase_name, phase_df in phases.items():
        if len(phase_df) < 50:
            print(f"  [WARN] Phase '{phase_name}' has only {len(phase_df)} samples — using defaults")
            phase_weights[phase_name] = dict(DEFAULT_WEIGHTS)
            phase_r2[phase_name] = 0.0
            continue

        X = phase_df[SE_FEATURE_COLS].values.astype(float)
        y = phase_df["final_score"].values.astype(float)
        lr = LinearRegression().fit(X, y)

        # Normalise coefficients: scale so max abs coefficient maps to
        # roughly the same range as DEFAULT_WEIGHTS (~0.3)
        coefs = lr.coef_
        max_abs = np.max(np.abs(coefs)) if np.max(np.abs(coefs)) > 0 else 1.0
        scale = 0.30 / max_abs
        normalised = coefs * scale

        weights = {
            FEATURE_NAMES[i]: float(normalised[i])
            for i in range(len(FEATURE_NAMES))
        }
        phase_weights[phase_name] = weights
        phase_r2[phase_name] = float(lr.score(X, y))

        print(f"  Phase '{phase_name}': R^2={phase_r2[phase_name]:.4f}, n={len(phase_df)}")
        for fname, w in sorted(weights.items(), key=lambda x: abs(x[1]), reverse=True):
            print(f"    {fname:>35s}: {w:+.4f}")

    return phase_weights


def _derive_single_calibrated_weights(df: pd.DataFrame) -> Dict[str, float]:
    """Run global linear regression on SE features and normalise."""
    X = df[SE_FEATURE_COLS].values.astype(float)
    y = df["final_score"].values.astype(float)
    lr = LinearRegression().fit(X, y)

    coefs = lr.coef_
    max_abs = np.max(np.abs(coefs)) if np.max(np.abs(coefs)) > 0 else 1.0
    scale = 0.30 / max_abs
    normalised = coefs * scale

    return {FEATURE_NAMES[i]: float(normalised[i]) for i in range(len(FEATURE_NAMES))}


# ---------------------------------------------------------------------------
# Feature importance bar chart
# ---------------------------------------------------------------------------


def _plot_feature_importance(
    coef_table: List[Dict],
    title: str,
    filename: Path,
    key: str = "coefficient",
):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    names = [c["feature"] for c in coef_table[:20]]
    vals = [c[key] for c in coef_table[:20]]

    fig, ax = plt.subplots(figsize=(10, max(6, len(names) * 0.35)))
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in vals]
    ax.barh(range(len(names)), vals, color=colors)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel(key.replace("_", " ").title())
    ax.set_title(title)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(str(filename), dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# SHAP summary plot
# ---------------------------------------------------------------------------


def _plot_shap_summary(rf_result: Dict, feature_cols: List[str], plot_dir: Path):
    if rf_result.get("shap_values") is None:
        return
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import shap
    except ImportError:
        return

    shap_vals = rf_result["shap_values"]
    fig = plt.figure(figsize=(10, 8))
    shap.summary_plot(
        shap_vals,
        feature_names=feature_cols,
        show=False,
        max_display=20,
    )
    fig = plt.gcf()
    fig.tight_layout()
    fig.savefig(str(plot_dir / "shap_summary.png"), dpi=150, bbox_inches="tight")
    plt.close("all")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Layer 6.1 feature importance analysis.")
    parser.add_argument("--input", type=str, default="data/layer6_selfplay.parquet")
    parser.add_argument("--output-dir", type=str, default="data")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    plot_dir = output_dir / "layer6_plots"

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        print("Run scripts/collect_layer6_data.py first.")
        sys.exit(1)

    df = pd.read_parquet(str(input_path))
    print(f"Loaded {len(df)} rows from {input_path}")
    print(f"  Games: {df['game_id'].nunique()}, Checkpoints: {df['checkpoint_index'].nunique()}")

    # Drop rows with missing final_score
    df = df.dropna(subset=["final_score"])
    print(f"  After dropping NaN scores: {len(df)} rows")

    # Check for required columns
    missing_se = [c for c in SE_FEATURE_COLS if c not in df.columns]
    if missing_se:
        print(f"ERROR: Missing state-evaluator columns: {missing_se}")
        sys.exit(1)

    results: Dict[str, Any] = {}

    # ---------------------------------------------------------------
    # 1. Linear regression on state-evaluator features (7 features)
    # ---------------------------------------------------------------
    print("\n--- Linear Regression (7 state-evaluator features) ---")
    lr_se = _run_linear_regression(df, SE_FEATURE_COLS, "final_score")
    print(f"  R^2 = {lr_se['r2']:.4f}  (CV: {lr_se['r2_cv_mean']:.4f} +/- {lr_se['r2_cv_std']:.4f})")
    print(f"  Top features:")
    for c in lr_se["coefficients"][:7]:
        sig = "*" if c["significant"] else " "
        print(f"    {sig} {c['feature']:>40s}: {c['coefficient']:+.4f}  [{c['ci_lower']:+.4f}, {c['ci_upper']:+.4f}]")
    results["linear_regression_se"] = {
        k: v for k, v in lr_se.items()
        if k not in ("residuals", "predictions")
    }

    # ---------------------------------------------------------------
    # 2. Linear regression on full winprob features (35 features)
    # ---------------------------------------------------------------
    from analytics.winprob.features import SNAPSHOT_FEATURE_COLUMNS
    wp_cols = [c for c in SNAPSHOT_FEATURE_COLUMNS if c in df.columns]
    print(f"\n--- Linear Regression (full {len(wp_cols)} winprob features) ---")
    lr_wp = _run_linear_regression(df, wp_cols, "final_score")
    print(f"  R^2 = {lr_wp['r2']:.4f}  (CV: {lr_wp['r2_cv_mean']:.4f} +/- {lr_wp['r2_cv_std']:.4f})")
    print(f"  Top 10 features:")
    for c in lr_wp["coefficients"][:10]:
        sig = "*" if c["significant"] else " "
        print(f"    {sig} {c['feature']:>45s}: {c['coefficient']:+.4f}")
    results["linear_regression_wp"] = {
        k: v for k, v in lr_wp.items()
        if k not in ("residuals", "predictions")
    }

    # ---------------------------------------------------------------
    # 3. Random Forest + SHAP on winprob features
    # ---------------------------------------------------------------
    print(f"\n--- Random Forest Regression ({len(wp_cols)} features) ---")
    rf_result = _run_random_forest(df, wp_cols, "final_score")
    print(f"  R^2 = {rf_result['r2']:.4f}  (CV: {rf_result['r2_cv_mean']:.4f} +/- {rf_result['r2_cv_std']:.4f})")
    print(f"  Top 10 importances (MDI):")
    for imp in rf_result["importances"][:10]:
        print(f"    {imp['feature']:>45s}: {imp['importance']:.4f}")
    if rf_result.get("shap_importances"):
        print(f"  Top 10 SHAP importances:")
        for s in rf_result["shap_importances"][:10]:
            print(f"    {s['feature']:>45s}: {s['mean_abs_shap']:.4f}")
    results["random_forest_wp"] = {
        k: v for k, v in rf_result.items()
        if k not in ("shap_values", "shap_sample_idx")
    }

    # ---------------------------------------------------------------
    # 4. Residual analysis (using SE linear regression)
    # ---------------------------------------------------------------
    print("\n--- Residual Analysis ---")
    resid_result = _residual_analysis(
        df, lr_se["residuals"], lr_se["predictions"], plot_dir,
    )
    print(f"  RMSE: {resid_result['rmse']:.2f}")
    print(f"  MAE:  {resid_result['mae']:.2f}")
    for phase, stats in resid_result["phase_residual_stats"].items():
        print(f"  Phase '{phase}': RMSE={stats['rmse']:.2f}, MAE={stats['mae']:.2f}, n={stats['count']}")
    results["residual_analysis"] = resid_result

    # ---------------------------------------------------------------
    # 5. Phase-dependent weights
    # ---------------------------------------------------------------
    print("\n--- Phase-Dependent Weight Calibration ---")
    phase_weights = _derive_phase_weights(df)
    results["phase_weights"] = phase_weights

    # ---------------------------------------------------------------
    # 6. Global calibrated weights
    # ---------------------------------------------------------------
    print("\n--- Global Calibrated Weights ---")
    single_weights = _derive_single_calibrated_weights(df)
    print("  Calibrated weights:")
    for k, v in sorted(single_weights.items(), key=lambda x: abs(x[1]), reverse=True):
        default_v = DEFAULT_WEIGHTS.get(k, 0.0)
        print(f"    {k:>35s}: {v:+.4f}  (was {default_v:+.2f})")
    results["calibrated_weights"] = single_weights

    # ---------------------------------------------------------------
    # 7. TD Learning decision
    # ---------------------------------------------------------------
    r2_se = lr_se["r2"]
    r2_wp = lr_wp["r2"]
    r2_rf = rf_result["r2"]
    print(f"\n--- TD Learning Decision ---")
    print(f"  R^2 (SE linear):   {r2_se:.4f}")
    print(f"  R^2 (WP linear):   {r2_wp:.4f}")
    print(f"  R^2 (WP RF):       {r2_rf:.4f}")

    if r2_se > 0.7:
        td_decision = "skip"
        td_reason = f"R^2={r2_se:.4f} > 0.7 — evaluation captures most variance. TD learning offers diminishing returns."
    elif r2_se < 0.5:
        td_decision = "implement"
        td_reason = f"R^2={r2_se:.4f} < 0.5 — substantial room for improvement. TD-UCT bootstrapping recommended."
    else:
        td_decision = "borderline"
        td_reason = f"R^2={r2_se:.4f} in [0.5, 0.7] — borderline. Monitor after deploying calibrated weights."

    print(f"  Decision: {td_decision}")
    print(f"  Reason:   {td_reason}")
    results["td_learning_decision"] = {
        "r2_se": r2_se,
        "r2_wp": r2_wp,
        "r2_rf": r2_rf,
        "decision": td_decision,
        "reason": td_reason,
    }

    # ---------------------------------------------------------------
    # Save results
    # ---------------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)

    # Analysis results (JSON-serialisable subset)
    json_path = output_dir / "layer6_analysis_results.json"
    with open(str(json_path), "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to {json_path}")

    # Calibrated weights
    weights_path = output_dir / "layer6_calibrated_weights.json"
    cal_output = {
        "single_weights": single_weights,
        "phase_weights": phase_weights,
        "default_weights": dict(DEFAULT_WEIGHTS),
    }
    with open(str(weights_path), "w") as f:
        json.dump(cal_output, f, indent=2)
    print(f"  Calibrated weights saved to {weights_path}")

    # Plots
    plot_dir.mkdir(parents=True, exist_ok=True)
    _plot_feature_importance(
        lr_wp["coefficients"],
        "Linear Regression Coefficients (Winprob Features)",
        plot_dir / "lr_coefs_winprob.png",
    )
    _plot_feature_importance(
        lr_se["coefficients"],
        "Linear Regression Coefficients (State Evaluator Features)",
        plot_dir / "lr_coefs_se.png",
    )
    _plot_feature_importance(
        rf_result["importances"],
        "Random Forest Feature Importance (MDI)",
        plot_dir / "rf_importance_mdi.png",
        key="importance",
    )
    if rf_result.get("shap_importances"):
        _plot_feature_importance(
            rf_result["shap_importances"],
            "SHAP Feature Importance (Mean |SHAP|)",
            plot_dir / "shap_importance.png",
            key="mean_abs_shap",
        )
        _plot_shap_summary(rf_result, wp_cols, plot_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()

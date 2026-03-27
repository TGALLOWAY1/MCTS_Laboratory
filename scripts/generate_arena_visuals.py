#!/usr/bin/env python3
"""Generate publication-ready arena visualizations across all MCTS layers.

Tells the story of incremental MCTS improvements from Layer 1 through Layer 9
using data from arena tournament runs and reports.

Reuses styling from analytics.baseline.plots (PR #94 visualization platform).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from analytics.baseline.plots import save_plot, setup_plot_style, annotate_threshold

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
ARENA_RUNS = ROOT / "arena_runs"
ARCHIVE_RUNS = ROOT / "archive" / "arena_runs"
OUTPUT_DIR = ROOT / "arena_visuals"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_summary(run_dir: Path) -> Dict[str, Any]:
    return json.loads((run_dir / "summary.json").read_text())


# ---------------------------------------------------------------------------
# Color palette (consistent across all plots)
# ---------------------------------------------------------------------------
LAYER_COLORS = {
    "L1": "#636363",
    "L2": "#9e9ac8",
    "L3": "#8c6d31",
    "L4": "#4c72b0",
    "L5": "#55a868",
    "L6": "#dd8452",
    "L9": "#c44e52",
}

AGENT_PALETTE = [
    "#2b83ba",  # blue
    "#abdda4",  # green
    "#fdae61",  # orange
    "#d7191c",  # red
    "#756bb1",  # purple
    "#66c2a5",  # teal
]


# ---------------------------------------------------------------------------
# Helper: horizontal bar chart for win rates
# ---------------------------------------------------------------------------

def _bar_chart(
    agents: List[str],
    values: List[float],
    title: str,
    xlabel: str,
    output_path: Path,
    colors: Optional[List[str]] = None,
    highlight_best: bool = True,
    value_fmt: str = "{:.0%}",
    annotations: Optional[List[str]] = None,
):
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(10, max(4, len(agents) * 0.7 + 1.5)))

    if colors is None:
        colors = AGENT_PALETTE[: len(agents)]

    best_idx = values.index(max(values)) if highlight_best else -1
    edge_colors = ["#333333" if i == best_idx else "black" for i in range(len(agents))]
    linewidths = [2.0 if i == best_idx else 0.5 for i in range(len(agents))]

    bars = ax.barh(
        range(len(agents)),
        values,
        color=colors,
        edgecolor=edge_colors,
        linewidth=linewidths,
        height=0.6,
    )

    for i, (bar, val) in enumerate(zip(bars, values)):
        label = value_fmt.format(val)
        if annotations:
            label += f"  {annotations[i]}"
        ax.text(
            bar.get_width() + max(values) * 0.02,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=10,
            fontweight="bold" if i == best_idx else "normal",
        )

    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels(agents, fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xlim(0, max(values) * 1.25)
    fig.tight_layout()
    save_plot(fig, output_path)


# ===========================================================================
# FIGURE 1: Layer-by-Layer Win Rate Progression
# ===========================================================================

def fig1_layer_progression():
    """Show the best agent win rate from each layer experiment."""
    # Data extracted from arena reports
    layers = [
        "L3: Progressive Widening\n(pw_alpha=0.5, pw_c=2.0)",
        "L4: Cutoff Depth\n(depth=5, 25 iter)",
        "L4: Rollout Policy\n(random)",
        "L4: Combined\n(random+d5+α=0.25)",
        "L5: RAVE k-sweep\n(k=1000)",
        "L5: Head-to-Head\n(RAVE only)",
        "L5: Convergence\n(RAVE@50ms)",
        "L6: Phase Eval\n(default weights)",
        "L6: Calibrated\n(calib eval d0)",
        "L9: Adaptive Depth",
    ]
    win_rates = [0.64, 0.54, 0.36, 0.36, 0.36, 0.447, 0.36, 0.48, 0.76, 0.36]
    layer_tags = ["L3", "L4", "L4", "L4", "L5", "L5", "L5", "L6", "L6", "L9"]
    colors = [LAYER_COLORS[t] for t in layer_tags]

    setup_plot_style()
    fig, ax = plt.subplots(figsize=(12, 7))

    bars = ax.barh(range(len(layers)), win_rates, color=colors, edgecolor="black",
                   linewidth=0.5, height=0.65)

    for bar, val in zip(bars, win_rates):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.0%}", va="center", fontsize=10, fontweight="bold")

    ax.axvline(x=0.25, color="gray", linestyle="--", alpha=0.5, linewidth=1)
    ax.text(0.25, -0.6, "Random baseline\n(25% = chance)", ha="center",
            fontsize=8, color="gray")

    ax.set_yticks(range(len(layers)))
    ax.set_yticklabels(layers, fontsize=9)
    ax.set_xlabel("Best Agent Win Rate in Tournament")
    ax.set_title("MCTS Arena: Best Agent Win Rate by Experiment", fontsize=14, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xlim(0, 0.85)

    # Legend
    handles = [mpatches.Patch(color=LAYER_COLORS[k], label=k) for k in ["L3", "L4", "L5", "L6", "L9"]]
    ax.legend(handles=handles, loc="lower right", fontsize=9)

    fig.tight_layout()
    save_plot(fig, OUTPUT_DIR / "01_layer_progression.png")
    print("  [1/9] Layer progression chart")


# ===========================================================================
# FIGURE 2: L3 — Progressive Widening Dominance
# ===========================================================================

def fig2_progressive_widening():
    """L3: Progressive Widening dominates baseline, PH, and PW+PH."""
    run = load_summary(ARENA_RUNS / "20260325_201856_32cf0875")
    agents_order = ["mcts_progressive_widening", "mcts_pw_plus_ph",
                    "mcts_baseline", "mcts_progressive_history"]
    labels = [
        "Progressive Widening",
        "PW + PH (combined)",
        "Baseline",
        "Progressive History",
    ]

    win_rates = [run["win_stats"][a]["win_rate"] for a in agents_order]
    mean_scores = [run["score_stats"][a]["mean"] for a in agents_order]

    # Pairwise: PW beats everyone convincingly
    pw_pairwise = {
        "vs Baseline": "22-3",
        "vs PH": "25-0",
        "vs PW+PH": "17-8",
    }

    setup_plot_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    colors = ["#2ca02c", "#ff7f0e", "#7f7f7f", "#9467bd"]

    # Win rate
    bars1 = ax1.bar(range(len(labels)), win_rates, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars1, win_rates):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.0%}", ha="center", fontsize=11, fontweight="bold")
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    ax1.set_ylabel("Win Rate")
    ax1.set_title("Win Rate", fontweight="bold")
    ax1.axhline(y=0.25, color="gray", linestyle="--", alpha=0.5)
    ax1.set_ylim(0, 0.8)

    # Mean score
    bars2 = ax2.bar(range(len(labels)), mean_scores, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars2, mean_scores):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{val:.1f}", ha="center", fontsize=10)
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    ax2.set_ylabel("Mean Score")
    ax2.set_title("Mean Score", fontweight="bold")

    # Add pairwise annotation
    pairwise_text = "\n".join(f"PW {k}: {v}" for k, v in pw_pairwise.items())
    ax2.text(0.97, 0.95, f"Pairwise H2H:\n{pairwise_text}",
             transform=ax2.transAxes, fontsize=8.5, va="top", ha="right",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#e8f5e9", alpha=0.9))

    fig.suptitle("Layer 3: Progressive Widening Dominates Action Reduction",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, OUTPUT_DIR / "02_L3_progressive_widening.png")
    print("  [2/9] L3 progressive widening")


# ===========================================================================
# FIGURE 3: L4 — Rollout Quality vs Iteration Quantity
# ===========================================================================

def fig3_quality_vs_quantity():
    """L4 headline: cutoff_5@25iter (54%) vs cutoff_0@1000iter (0%)."""
    run = load_summary(ARENA_RUNS / "20260325_164035_0a7ca009")
    agents_order = ["cutoff_5_25iter", "cutoff_0_1000iter", "cutoff_10_25iter", "cutoff_0_25iter"]
    labels = [
        "Depth 5 @ 25 iter",
        "Depth 0 @ 1000 iter",
        "Depth 10 @ 25 iter",
        "Depth 0 @ 25 iter",
    ]

    win_rates = [run["win_stats"][a]["win_rate"] for a in agents_order]
    mean_scores = [run["score_stats"][a]["mean"] for a in agents_order]
    avg_ms = [run["time_sim_efficiency"][a]["avg_time_ms_per_move"] for a in agents_order]

    setup_plot_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Win rate bars
    colors = [AGENT_PALETTE[0], AGENT_PALETTE[3], AGENT_PALETTE[2], AGENT_PALETTE[1]]
    bars1 = ax1.bar(range(len(labels)), win_rates, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars1, win_rates):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.0%}", ha="center", fontsize=11, fontweight="bold")
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    ax1.set_ylabel("Win Rate")
    ax1.set_title("Win Rate: Rollout Quality Beats Quantity", fontweight="bold")
    ax1.axhline(y=0.25, color="gray", linestyle="--", alpha=0.5)
    ax1.set_ylim(0, 0.7)

    # Efficiency scatter: ms/move vs win rate
    ax2.scatter(avg_ms, win_rates, s=200, c=colors, edgecolors="black", zorder=5)
    for i, label in enumerate(labels):
        ax2.annotate(label, (avg_ms[i], win_rates[i]),
                     textcoords="offset points", xytext=(8, 8), fontsize=8)
    ax2.set_xlabel("Avg ms / move")
    ax2.set_ylabel("Win Rate")
    ax2.set_title("Efficiency: Time vs Win Rate", fontweight="bold")
    ax2.axhline(y=0.25, color="gray", linestyle="--", alpha=0.5)

    fig.suptitle("Layer 4: Rollout Simulation Strategy", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, OUTPUT_DIR / "03_L4_quality_vs_quantity.png")
    print("  [3/9] L4 quality vs quantity")


# ===========================================================================
# FIGURE 4: L4 — Rollout Policy Comparison
# ===========================================================================

def fig4_rollout_policy():
    """Compare heuristic vs random vs two-ply rollout policies."""
    run = load_summary(ARENA_RUNS / "20260325_165028_feca38f3")
    agents_order = ["random_cutoff8_25iter", "two_ply_all_cutoff8_25iter",
                    "two_ply_k10_cutoff8_25iter", "heuristic_cutoff8_25iter"]
    labels = ["Random", "Two-Ply (all)", "Two-Ply (K=10)", "Heuristic (default)"]

    win_rates = [run["win_stats"][a]["win_rate"] for a in agents_order]
    ms_per_move = [run["time_sim_efficiency"][a]["avg_time_ms_per_move"] for a in agents_order]
    score_per_sec = [run["time_sim_efficiency"][a]["score_per_second"] or 0 for a in agents_order]

    setup_plot_style()
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    colors = [AGENT_PALETTE[0], AGENT_PALETTE[1], AGENT_PALETTE[2], AGENT_PALETTE[3]]

    # Win rate
    bars = axes[0].bar(range(len(labels)), win_rates, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars, win_rates):
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                     f"{val:.0%}", ha="center", fontsize=10, fontweight="bold")
    axes[0].set_xticks(range(len(labels)))
    axes[0].set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    axes[0].set_ylabel("Win Rate")
    axes[0].set_title("Win Rate", fontweight="bold")
    axes[0].axhline(y=0.25, color="gray", linestyle="--", alpha=0.5)
    axes[0].set_ylim(0, 0.5)

    # Time per move
    bars2 = axes[1].bar(range(len(labels)), ms_per_move, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars2, ms_per_move):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                     f"{val:.0f}ms", ha="center", fontsize=9)
    axes[1].set_xticks(range(len(labels)))
    axes[1].set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    axes[1].set_ylabel("ms / move")
    axes[1].set_title("Compute Cost", fontweight="bold")

    # Score efficiency
    bars3 = axes[2].bar(range(len(labels)), score_per_sec, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars3, score_per_sec):
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                     f"{val:.1f}", ha="center", fontsize=9)
    axes[2].set_xticks(range(len(labels)))
    axes[2].set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    axes[2].set_ylabel("Score / second")
    axes[2].set_title("Score Efficiency", fontweight="bold")

    fig.suptitle("Layer 4: Rollout Policy — Random Wins on Quality AND Efficiency",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, OUTPUT_DIR / "04_L4_rollout_policy.png")
    print("  [4/9] L4 rollout policy comparison")


# ===========================================================================
# FIGURE 5: L5 — RAVE Convergence Speedup
# ===========================================================================

def fig5_rave_convergence():
    """RAVE@50ms beats baseline@200ms — 4x effective speedup."""
    run = load_summary(ARCHIVE_RUNS / "20260325_210306_4024cab3")
    agents_order = ["mcts_rave_50ms", "mcts_rave_200ms", "mcts_baseline_50ms", "mcts_baseline_200ms"]
    labels = ["RAVE @ 50ms\n(12 iter)", "RAVE @ 200ms\n(50 iter)",
              "Baseline @ 50ms\n(12 iter)", "Baseline @ 200ms\n(50 iter)"]

    win_rates = [run["win_stats"][a]["win_rate"] for a in agents_order]
    mean_scores = [run["score_stats"][a]["mean"] for a in agents_order]

    setup_plot_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    colors = ["#2ca02c", "#98df8a", "#d62728", "#ff9896"]

    # Win rate
    bars1 = ax1.bar(range(len(labels)), win_rates, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars1, win_rates):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.0%}", ha="center", fontsize=11, fontweight="bold")
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylabel("Win Rate")
    ax1.set_title("Win Rate", fontweight="bold")
    ax1.axhline(y=0.25, color="gray", linestyle="--", alpha=0.5)
    ax1.set_ylim(0, 0.5)

    # Annotate the key insight
    ax1.annotate("RAVE@50ms beats\nBaseline@200ms!",
                 xy=(0, win_rates[0]), xytext=(1.5, 0.44),
                 fontsize=10, fontweight="bold", color="#2ca02c",
                 arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=1.5))

    # Mean score
    bars2 = ax2.bar(range(len(labels)), mean_scores, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars2, mean_scores):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f"{val:.1f}", ha="center", fontsize=10)
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, fontsize=9)
    ax2.set_ylabel("Mean Score")
    ax2.set_title("Mean Score", fontweight="bold")

    fig.suptitle("Layer 5: RAVE Provides 4x Effective Convergence Speedup",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, OUTPUT_DIR / "05_L5_rave_convergence.png")
    print("  [5/9] L5 RAVE convergence")


# ===========================================================================
# FIGURE 6: L5 — RAVE vs Progressive History
# ===========================================================================

def fig6_rave_vs_ph():
    """RAVE alone (44.7%) vs PH+RAVE (26.7%) — PH hurts when combined with RAVE."""
    run = load_summary(ARCHIVE_RUNS / "20260325_210306_ed7ec9aa")
    agents_order = ["mcts_rave_only", "mcts_ph_plus_rave", "mcts_ph_only", "mcts_baseline"]
    labels = ["RAVE only", "PH + RAVE", "PH only", "Baseline"]

    win_rates = [run["win_stats"][a]["win_rate"] for a in agents_order]
    ts_mu = [None, None, None, None]
    for entry in run["trueskill_ratings"]["leaderboard"]:
        if entry["agent_id"] in agents_order:
            idx = agents_order.index(entry["agent_id"])
            ts_mu[idx] = entry["mu"]

    setup_plot_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    colors = ["#2ca02c", "#ff7f0e", "#9467bd", "#7f7f7f"]

    # Win rate
    bars1 = ax1.bar(range(len(labels)), win_rates, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars1, win_rates):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.1%}", ha="center", fontsize=11, fontweight="bold")
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, fontsize=10)
    ax1.set_ylabel("Win Rate")
    ax1.set_title("Win Rate", fontweight="bold")
    ax1.axhline(y=0.25, color="gray", linestyle="--", alpha=0.5)
    ax1.set_ylim(0, 0.55)

    # Draw arrow showing PH hurts RAVE
    ax1.annotate("PH dilutes\nRAVE signal",
                 xy=(1, win_rates[1]), xytext=(2, 0.40),
                 fontsize=10, fontweight="bold", color="#d62728",
                 arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.5))

    # TrueSkill
    bars2 = ax2.bar(range(len(labels)), ts_mu, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars2, ts_mu):
        if val is not None:
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                     f"{val:.1f}", ha="center", fontsize=10)
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, fontsize=10)
    ax2.set_ylabel("TrueSkill μ")
    ax2.set_title("TrueSkill Rating", fontweight="bold")

    fig.suptitle("Layer 5: RAVE Alone Dominates — Progressive History Hurts",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, OUTPUT_DIR / "06_L5_rave_vs_ph.png")
    print("  [6/9] L5 RAVE vs Progressive History")


# ===========================================================================
# FIGURE 7: L6 — Phase Eval Failure + Calibrated Weights
# ===========================================================================

def fig7_evaluation_refinement():
    """Phase-dependent eval scores 0% wins; calibrated vs default are tied."""
    run = load_summary(ARENA_RUNS / "20260325_033805_9b3944b6")
    agents_order = ["mcts_default_eval_d0", "mcts_calibrated_d0",
                    "mcts_phase_eval_d0", "mcts_phase_eval_rave_d0"]
    labels = ["Default Weights", "Calibrated Weights",
              "Phase-Dependent", "Phase + RAVE"]

    win_rates = [run["win_stats"][a]["win_rate"] for a in agents_order]
    mean_scores = [run["score_stats"][a]["mean"] for a in agents_order]

    setup_plot_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    colors = ["#2b83ba", "#abdda4", "#fdae61", "#d7191c"]

    # Win rate
    bars1 = ax1.bar(range(len(labels)), win_rates, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars1, win_rates):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.0%}", ha="center", fontsize=11, fontweight="bold")
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, fontsize=9, rotation=10, ha="right")
    ax1.set_ylabel("Win Rate")
    ax1.set_title("Win Rate", fontweight="bold")
    ax1.set_ylim(0, 0.65)

    # Add failure annotation
    ax1.annotate("Phase eval: 0% wins\n(inverted early weights,\nmissing center_proximity)",
                 xy=(2.5, 0.01), xytext=(2.5, 0.35),
                 fontsize=9, color="#d62728", fontweight="bold",
                 ha="center",
                 arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.5))

    # Mean score
    bars2 = ax2.bar(range(len(labels)), mean_scores, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars2, mean_scores):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{val:.1f}", ha="center", fontsize=10)
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, fontsize=9, rotation=10, ha="right")
    ax2.set_ylabel("Mean Score")
    ax2.set_title("Mean Score", fontweight="bold")

    fig.suptitle("Layer 6: Evaluation Refinement — Phase Weights Catastrophically Fail",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, OUTPUT_DIR / "07_L6_evaluation.png")
    print("  [7/9] L6 evaluation refinement")


# ===========================================================================
# FIGURE 8: L9 — Meta-Optimization: Adaptive Depth vs Adaptive C
# ===========================================================================

def fig8_meta_optimization():
    """Adaptive depth helps (36%, 1.64x faster); adaptive C is harmful (8%)."""
    # Data from layer9 report (run not in local arena_runs)
    agents = ["L9_adaptive_depth", "L9_baseline", "L9_full", "L9_adaptive_c"]
    win_rates = [0.36, 0.32, 0.24, 0.08]
    avg_ms = [1315, 2162, 1348, 2432]
    mean_scores = [72.96, 75.76, 71.72, 69.92]
    speedup = [1.64, 1.0, 1.60, 0.89]

    labels = [
        "Adaptive Depth",
        "Baseline",
        "Full (all L9)",
        "Adaptive C",
    ]

    setup_plot_style()
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

    colors = ["#2ca02c", "#7f7f7f", "#ff7f0e", "#d62728"]

    # Win rate
    bars1 = axes[0].bar(range(len(labels)), win_rates, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars1, win_rates):
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                     f"{val:.0%}", ha="center", fontsize=11, fontweight="bold")
    axes[0].set_xticks(range(len(labels)))
    axes[0].set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    axes[0].set_ylabel("Win Rate")
    axes[0].set_title("Win Rate", fontweight="bold")
    axes[0].axhline(y=0.25, color="gray", linestyle="--", alpha=0.5)
    axes[0].set_ylim(0, 0.5)

    # Speed
    bars2 = axes[1].bar(range(len(labels)), avg_ms, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars2, avg_ms):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30,
                     f"{val:,.0f}ms", ha="center", fontsize=9)
    axes[1].set_xticks(range(len(labels)))
    axes[1].set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    axes[1].set_ylabel("Avg ms / move")
    axes[1].set_title("Compute Time per Move", fontweight="bold")

    # Efficiency: win rate vs speed (bubble)
    for i in range(len(agents)):
        axes[2].scatter(avg_ms[i], win_rates[i], s=300, c=colors[i],
                        edgecolors="black", zorder=5)
        axes[2].annotate(labels[i], (avg_ms[i], win_rates[i]),
                         textcoords="offset points", xytext=(10, 8), fontsize=9)
    axes[2].set_xlabel("Avg ms / move")
    axes[2].set_ylabel("Win Rate")
    axes[2].set_title("Speed-Quality Tradeoff", fontweight="bold")
    axes[2].axhline(y=0.25, color="gray", linestyle="--", alpha=0.5)

    # Draw arrow for adaptive depth advantage
    axes[2].annotate("Faster AND\nbetter!",
                     xy=(avg_ms[0], win_rates[0]),
                     xytext=(1700, 0.42),
                     fontsize=10, fontweight="bold", color="#2ca02c",
                     arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=2))

    fig.suptitle("Layer 9: Meta-Optimization — Adaptive Depth Wins, Adaptive C Harms",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, OUTPUT_DIR / "08_L9_meta_optimization.png")
    print("  [8/9] L9 meta-optimization")


# ===========================================================================
# FIGURE 9: Grand Summary — Key Insights
# ===========================================================================

def fig9_grand_summary():
    """Multi-panel summary: key discoveries, recommended config, TrueSkill progression."""
    setup_plot_style()
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))

    # Panel 1: Key findings as annotated bar chart
    findings = [
        ("Prog. Widening dominates\n(64% win rate, 92.4 mean score)", 0.64, LAYER_COLORS["L3"]),
        ("Rollout depth 5 > depth 0\n@ 40x fewer iterations", 0.54, LAYER_COLORS["L4"]),
        ("Random rollout > heuristic\n(10x faster, higher win rate)", 0.36, LAYER_COLORS["L4"]),
        ("RAVE alone > RAVE + PH\n(PH dilutes RAVE signal)", 0.447, LAYER_COLORS["L5"]),
        ("RAVE @ 50ms > baseline @ 200ms\n(4x convergence speedup)", 0.36, LAYER_COLORS["L5"]),
        ("Calibrated eval ≈ default\n(missing center_proximity)", 0.52, LAYER_COLORS["L6"]),
        ("Phase-dep eval: 0% wins\n(inverted weights, noise)", 0.0, LAYER_COLORS["L6"]),
        ("Adaptive depth: faster + better\n(1.64x speedup, #1 rank)", 0.36, LAYER_COLORS["L9"]),
        ("Adaptive C: harmful with RAVE\n(8% win rate, worst)", 0.08, LAYER_COLORS["L9"]),
    ]

    labels = [f[0] for f in findings]
    values = [f[1] for f in findings]
    colors = [f[2] for f in findings]

    bars = axes[0].barh(range(len(labels)), values, color=colors, edgecolor="black",
                        linewidth=0.5, height=0.7)
    for bar, val in zip(bars, values):
        axes[0].text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                     f"{val:.0%}", va="center", fontsize=10, fontweight="bold")
    axes[0].set_yticks(range(len(labels)))
    axes[0].set_yticklabels(labels, fontsize=8.5)
    axes[0].set_xlabel("Best Agent Win Rate")
    axes[0].set_title("Key Findings Across All Layers", fontweight="bold")
    axes[0].invert_yaxis()
    axes[0].axvline(x=0.25, color="gray", linestyle="--", alpha=0.5)
    axes[0].set_xlim(0, 0.75)

    # Panel 2: Recommended configuration evolution
    config_labels = [
        "Baseline\n(L1)",
        "After L3\n(Prog. Widen)",
        "After L4\n(Simulation)",
        "After L5\n(RAVE)",
        "After L9\n(Meta-Opt)",
    ]
    # Using score_per_second as efficiency metric
    efficiency = [20.0, 166.9, 121.6, 386.1, 55.5]  # score/sec from reports
    win_improvement = [0.25, 0.64, 0.54, 0.447, 0.36]

    x = np.arange(len(config_labels))
    width = 0.35

    bars_eff = axes[1].bar(x - width / 2, efficiency, width, color="#4c72b0",
                            label="Score / second", edgecolor="black", linewidth=0.5)
    ax2_twin = axes[1].twinx()
    bars_win = ax2_twin.bar(x + width / 2, win_improvement, width, color="#55a868",
                             label="Best Win Rate", edgecolor="black", linewidth=0.5)

    axes[1].set_xlabel("Configuration Stage")
    axes[1].set_ylabel("Score / second (efficiency)", color="#4c72b0")
    ax2_twin.set_ylabel("Best Win Rate", color="#55a868")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(config_labels, fontsize=9)
    axes[1].set_title("Efficiency & Strength Through Optimization", fontweight="bold")

    # Combine legends
    lines1, labels1 = axes[1].get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    axes[1].legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)

    fig.suptitle("MCTS Laboratory: 10-Layer Optimization Summary",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, OUTPUT_DIR / "09_grand_summary.png")
    print("  [9/9] Grand summary")


# ===========================================================================
# Main
# ===========================================================================

def main():
    print(f"Generating arena visualizations in {OUTPUT_DIR}/\n")
    fig1_layer_progression()
    fig2_progressive_widening()
    fig3_quality_vs_quantity()
    fig4_rollout_policy()
    fig5_rave_convergence()
    fig6_rave_vs_ph()
    fig7_evaluation_refinement()
    fig8_meta_optimization()
    fig9_grand_summary()
    print(f"\nDone! 9 figures saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()

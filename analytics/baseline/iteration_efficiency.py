"""1.2 — Iteration Efficiency Analysis.

Computes the effective utilization ratio per turn: what fraction of total
MCTS iterations are spent on the eventually-selected move's subtree.

    utilization(turn) = visits_on_selected_move / total_iterations
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analytics.baseline.plots import annotate_threshold, save_plot, setup_plot_style


def compute_utilization_curve(
    steps: List[Dict[str, Any]],
) -> Dict[int, Dict[str, float]]:
    """Compute utilization ratio per step, grouped by turn_index.

    Utilization = best_move_visits / iterations.

    Steps without MCTS diagnostics are skipped.

    Returns a dict mapping turn_index -> {mean, std, count}.
    """
    by_turn: Dict[int, List[float]] = defaultdict(list)
    for step in steps:
        turn = step.get("turn_index")
        diag = step.get("mcts_diagnostics")
        if turn is None or not diag:
            continue
        best_visits = diag.get("best_move_visits")
        iterations = diag.get("iterations")
        if best_visits is None or iterations is None or iterations == 0:
            continue
        utilization = float(best_visits) / float(iterations)
        by_turn[turn].append(utilization)

    curve: Dict[int, Dict[str, float]] = {}
    for turn in sorted(by_turn):
        values = by_turn[turn]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n if n > 1 else 0.0
        std = math.sqrt(variance)
        curve[turn] = {"mean": mean, "std": std, "count": n}
    return curve


def summarize_utilization(
    curve: Dict[int, Dict[str, float]],
) -> Dict[str, Any]:
    """Produce summary statistics for the utilization curve.

    Returns overall mean utilization, turns below 50%, turns above 90%.
    """
    if not curve:
        return {
            "overall_mean": None,
            "turns_below_50pct": 0,
            "turns_above_90pct": 0,
            "total_turns": 0,
        }
    all_means = [v["mean"] for v in curve.values()]
    overall = sum(all_means) / len(all_means)
    below_50 = sum(1 for m in all_means if m < 0.50)
    above_90 = sum(1 for m in all_means if m > 0.90)
    return {
        "overall_mean": overall,
        "turns_below_50pct": below_50,
        "turns_above_90pct": above_90,
        "total_turns": len(all_means),
    }


def plot_utilization_curve(
    curve: Dict[int, Dict[str, float]],
    output_path: str | Path,
    title: Optional[str] = None,
) -> None:
    """Plot utilization ratio vs turn number with threshold annotations."""
    setup_plot_style()
    fig, ax = plt.subplots()

    turns = sorted(curve.keys())
    means = [curve[t]["mean"] for t in turns]
    stds = [curve[t]["std"] for t in turns]

    ax.plot(turns, means, color="darkorange", linewidth=2, label="Mean utilization")
    ax.fill_between(
        turns,
        [max(0, m - s) for m, s in zip(means, stds)],
        [min(1, m + s) for m, s in zip(means, stds)],
        alpha=0.2,
        color="darkorange",
        label="±1 std dev",
    )

    annotate_threshold(ax, 0.50, "50% — search spreading thin", color="red")
    annotate_threshold(ax, 0.90, "90% — over-exploiting", color="purple")

    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Turn number (ply)")
    ax.set_ylabel("Utilization ratio (best_visits / iterations)")
    ax.set_title(title or "1.2 — Iteration Efficiency (Utilization Ratio)")
    ax.legend(loc="upper right")
    save_plot(fig, output_path)

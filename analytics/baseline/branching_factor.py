"""1.1 — Branching Factor Curve analysis.

Computes and plots the average branching factor (number of legal moves)
by game turn number across all logged games.
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analytics.baseline.plots import annotate_peak, save_plot, setup_plot_style


def compute_branching_factor_curve(
    steps: List[Dict[str, Any]],
) -> Dict[int, Dict[str, float]]:
    """Group steps by ``turn_index`` and compute branching-factor statistics.

    The branching factor for a step is ``legal_moves_before`` (the number of
    legal moves available to the player at that turn).

    Returns a dict mapping turn_index -> {mean, std, count, min, max}.
    """
    by_turn: Dict[int, List[int]] = defaultdict(list)
    for step in steps:
        turn = step.get("turn_index")
        bf = step.get("legal_moves_before")
        if turn is None or bf is None:
            continue
        by_turn[turn].append(int(bf))

    curve: Dict[int, Dict[str, float]] = {}
    for turn in sorted(by_turn):
        values = by_turn[turn]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n if n > 1 else 0.0
        std = math.sqrt(variance)
        curve[turn] = {
            "mean": mean,
            "std": std,
            "count": n,
            "min": float(min(values)),
            "max": float(max(values)),
        }
    return curve


def find_peak(
    curve: Dict[int, Dict[str, float]],
    iteration_budget: int = 2000,
) -> Dict[str, Any]:
    """Find the peak branching factor and compute implied visits-per-child.

    Args:
        curve: Output of :func:`compute_branching_factor_curve`.
        iteration_budget: MCTS iteration count per move.

    Returns:
        Dict with peak_turn, peak_bf, implied_visits_per_child.
    """
    if not curve:
        return {
            "peak_turn": None,
            "peak_bf": 0.0,
            "implied_visits_per_child": 0.0,
        }
    peak_turn = max(curve, key=lambda t: curve[t]["mean"])
    peak_bf = curve[peak_turn]["mean"]
    visits_per_child = iteration_budget / peak_bf if peak_bf > 0 else float("inf")
    return {
        "peak_turn": peak_turn,
        "peak_bf": peak_bf,
        "peak_std": curve[peak_turn]["std"],
        "implied_visits_per_child": visits_per_child,
        "iteration_budget": iteration_budget,
    }


def plot_branching_factor_curve(
    curve: Dict[int, Dict[str, float]],
    peak_info: Dict[str, Any],
    output_path: str | Path,
    title: Optional[str] = None,
) -> None:
    """Plot mean +/- std branching factor vs turn number.

    Marks the peak and annotates with implied visits-per-child.
    """
    setup_plot_style()
    fig, ax = plt.subplots()

    turns = sorted(curve.keys())
    means = [curve[t]["mean"] for t in turns]
    stds = [curve[t]["std"] for t in turns]

    ax.plot(turns, means, color="steelblue", linewidth=2, label="Mean branching factor")
    ax.fill_between(
        turns,
        [m - s for m, s in zip(means, stds)],
        [m + s for m, s in zip(means, stds)],
        alpha=0.2,
        color="steelblue",
        label="±1 std dev",
    )

    # Annotate peak
    pt = peak_info.get("peak_turn")
    if pt is not None and pt in curve:
        pbf = peak_info["peak_bf"]
        vpc = peak_info["implied_visits_per_child"]
        budget = peak_info.get("iteration_budget", "?")
        annotate_peak(
            ax,
            pt,
            pbf,
            f"Peak: {pbf:.0f} moves @ turn {pt}\n"
            f"~{vpc:.1f} visits/child ({budget} iters)",
        )

    ax.set_xlabel("Turn number (ply)")
    ax.set_ylabel("Branching factor (legal moves)")
    ax.set_title(title or "1.1 — Branching Factor Curve")
    ax.legend(loc="upper right")
    save_plot(fig, output_path)

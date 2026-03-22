"""1.5 — Seat-Position Bias Analysis.

Computes average score by seat position (P1–P4) across all games and
tests for statistical significance of first-mover advantage.
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analytics.baseline.plots import save_plot, setup_plot_style


def compute_seat_bias(
    games: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute score statistics by seat position with significance tests.

    Each game record contains ``seat_assignment`` (player_id -> agent_name)
    and ``final_scores`` (player_id -> score).  Since all agents are
    identical in self-play, we group by player_id (= seat index + 1).

    Returns per-seat stats, ANOVA p-value, and pairwise KS tests.
    """
    scores_by_seat: Dict[int, List[int]] = defaultdict(list)

    for game in games:
        final_scores = game.get("final_scores", {})
        for player_id_str, score in final_scores.items():
            seat = int(player_id_str)
            scores_by_seat[seat].append(int(score))

    per_seat: Dict[int, Dict[str, Any]] = {}
    for seat in sorted(scores_by_seat):
        values = scores_by_seat[seat]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n if n > 1 else 0.0
        std = math.sqrt(variance)
        se = std / math.sqrt(n) if n > 0 else 0.0
        ci_95 = 1.96 * se
        per_seat[seat] = {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "se": round(se, 2),
            "ci_95_lower": round(mean - ci_95, 2),
            "ci_95_upper": round(mean + ci_95, 2),
            "count": n,
            "min": min(values),
            "max": max(values),
        }

    # ANOVA test (one-way) — are seat means significantly different?
    anova_result = _anova_oneway(scores_by_seat)

    # Pairwise KS tests between seats
    pairwise_ks = _pairwise_ks(scores_by_seat)

    return {
        "per_seat": per_seat,
        "anova": anova_result,
        "pairwise_ks": pairwise_ks,
        "total_games": len(games),
    }


def _anova_oneway(
    groups: Dict[int, List[int]],
) -> Dict[str, Any]:
    """Simple one-way ANOVA using scipy if available, else manual."""
    try:
        from scipy import stats

        group_lists = [groups[k] for k in sorted(groups) if groups[k]]
        if len(group_lists) < 2:
            return {"f_statistic": None, "p_value": None, "method": "scipy"}
        f_stat, p_value = stats.f_oneway(*group_lists)
        return {
            "f_statistic": round(float(f_stat), 4),
            "p_value": round(float(p_value), 6),
            "method": "scipy.stats.f_oneway",
        }
    except ImportError:
        return _manual_anova(groups)


def _manual_anova(
    groups: Dict[int, List[int]],
) -> Dict[str, Any]:
    """Fallback one-way ANOVA without scipy."""
    all_values = []
    for vals in groups.values():
        all_values.extend(vals)
    if not all_values:
        return {"f_statistic": None, "p_value": None, "method": "manual"}

    grand_mean = sum(all_values) / len(all_values)
    k = len(groups)
    n_total = len(all_values)

    # Between-group sum of squares
    ss_between = sum(
        len(vals) * (sum(vals) / len(vals) - grand_mean) ** 2
        for vals in groups.values()
        if vals
    )
    # Within-group sum of squares
    ss_within = sum(
        sum((v - sum(vals) / len(vals)) ** 2 for v in vals)
        for vals in groups.values()
        if vals
    )

    df_between = k - 1
    df_within = n_total - k
    if df_between <= 0 or df_within <= 0 or ss_within == 0:
        return {"f_statistic": None, "p_value": None, "method": "manual"}

    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    f_stat = ms_between / ms_within

    return {
        "f_statistic": round(f_stat, 4),
        "p_value": None,  # no p-value without scipy
        "method": "manual (no scipy — install scipy for p-value)",
    }


def _pairwise_ks(
    groups: Dict[int, List[int]],
) -> List[Dict[str, Any]]:
    """Pairwise Kolmogorov-Smirnov tests between seat groups."""
    try:
        from scipy import stats
    except ImportError:
        return []

    seats = sorted(groups.keys())
    results: List[Dict[str, Any]] = []
    for i in range(len(seats)):
        for j in range(i + 1, len(seats)):
            a, b = groups[seats[i]], groups[seats[j]]
            if not a or not b:
                continue
            ks_stat, p_value = stats.ks_2samp(a, b)
            results.append(
                {
                    "seat_a": seats[i],
                    "seat_b": seats[j],
                    "ks_statistic": round(float(ks_stat), 4),
                    "p_value": round(float(p_value), 6),
                }
            )
    return results


def plot_seat_bias(
    result: Dict[str, Any],
    output_path: str | Path,
    title: Optional[str] = None,
) -> None:
    """Bar chart of average score by seat with 95% CI error bars."""
    setup_plot_style()
    fig, ax = plt.subplots()

    per_seat = result.get("per_seat", {})
    seats = sorted(per_seat.keys())
    means = [per_seat[s]["mean"] for s in seats]
    ci_lower = [per_seat[s]["mean"] - per_seat[s]["ci_95_lower"] for s in seats]
    ci_upper = [per_seat[s]["ci_95_upper"] - per_seat[s]["mean"] for s in seats]

    colors = ["#4c72b0", "#55a868", "#c44e52", "#8172b2"]
    x_labels = [f"P{s} (Seat {s})" for s in seats]

    bars = ax.bar(
        range(len(seats)),
        means,
        yerr=[ci_lower, ci_upper],
        capsize=5,
        color=colors[: len(seats)],
        edgecolor="black",
        linewidth=0.5,
    )

    ax.set_xticks(range(len(seats)))
    ax.set_xticklabels(x_labels)
    ax.set_ylabel("Average Score")

    anova = result.get("anova", {})
    p_val = anova.get("p_value")
    p_text = f"p={p_val:.4f}" if p_val is not None else "p=N/A"
    ax.set_title(
        (title or "1.5 — Seat-Position Bias") + f"\nANOVA: F={anova.get('f_statistic', 'N/A')}, {p_text}"
    )

    # Annotate bars with mean values
    for bar, mean in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{mean:.1f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    save_plot(fig, output_path)

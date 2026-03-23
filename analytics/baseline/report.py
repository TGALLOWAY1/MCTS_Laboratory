"""Generate a comprehensive markdown baseline report from Layer 1 results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def generate_baseline_report(
    results: Dict[str, Any],
    output_path: str | Path,
) -> None:
    """Write a markdown report summarising all Layer 1 analyses.

    ``results`` should contain keys produced by the master orchestration
    script: ``branching_factor``, ``iteration_efficiency``,
    ``simulation_quality``, ``qvalue_convergence``, ``seat_bias``.
    """
    sections = [
        _header(),
        _section_branching_factor(results.get("branching_factor", {})),
        _section_iteration_efficiency(results.get("iteration_efficiency", {})),
        _section_simulation_quality(results.get("simulation_quality", {})),
        _section_qvalue_convergence(results.get("qvalue_convergence", {})),
        _section_seat_bias(results.get("seat_bias", {})),
        _section_key_decisions(results),
        _section_checklist(results),
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")


# ------------------------------------------------------------------
# Section builders
# ------------------------------------------------------------------


def _header() -> str:
    return (
        "# Layer 1: Baseline Characterization Report\n\n"
        "> **Status**: DIAGNOSTIC — data collected with the current agent, "
        "no algorithm changes.\n>\n"
        "> This report documents the current MCTS agent's behaviour across "
        "500+ self-play games and identifies the highest-impact areas for "
        "subsequent optimisation layers."
    )


def _section_branching_factor(data: Dict[str, Any]) -> str:
    peak = data.get("peak", {})
    pt = peak.get("peak_turn", "?")
    pbf = peak.get("peak_bf", 0)
    vpc = peak.get("implied_visits_per_child", 0)
    budget = peak.get("iteration_budget", "?")
    curve = data.get("curve", {})
    n_turns = len(curve)

    return (
        "## 1.1 — Branching Factor Curve\n\n"
        f"Measured across **{n_turns}** distinct turn indices.\n\n"
        f"- **Peak branching factor**: {pbf:.0f} legal moves at turn {pt}\n"
        f"- **Implied visits/child** at {budget} iterations: **{vpc:.1f}**\n"
        f"- This is where search budget is most strained.\n\n"
        "![Branching Factor Curve](plots/branching_factor_curve.png)"
    )


def _section_iteration_efficiency(data: Dict[str, Any]) -> str:
    summary = data.get("summary", {})
    overall = summary.get("overall_mean")
    below_50 = summary.get("turns_below_50pct", 0)
    above_90 = summary.get("turns_above_90pct", 0)
    total = summary.get("total_turns", 0)

    overall_str = f"{overall:.1%}" if overall is not None else "N/A"

    return (
        "## 1.2 — Iteration Efficiency\n\n"
        f"- **Overall mean utilization**: {overall_str}\n"
        f"- Turns below 50% (search spreading thin): **{below_50}** / {total}\n"
        f"- Turns above 90% (over-exploiting): **{above_90}** / {total}\n\n"
        "![Utilization Curve](plots/utilization_curve.png)"
    )


def _section_simulation_quality(data: Dict[str, Any]) -> str:
    h_avg = data.get("heuristic_avg_score", 0)
    m_avg = data.get("mcts_avg_score", 0)
    delta = data.get("delta", 0)
    h_games = data.get("heuristic_num_games", 0)
    m_games = data.get("mcts_num_games", 0)
    rank_dist = data.get("heuristic_rank_distribution", {})

    rank_lines = " | ".join(f"Rank {r}: {c}" for r, c in sorted(rank_dist.items()))

    return (
        "## 1.3 — Simulation Quality Audit\n\n"
        "| Metric | Heuristic-only | Full MCTS | Delta |\n"
        "|--------|---------------|-----------|-------|\n"
        f"| Avg Score | {h_avg:.1f} | {m_avg:.1f} | {delta:+.1f} |\n"
        f"| Games | {h_games} | {m_games} | — |\n\n"
        f"**Heuristic rank distribution**: {rank_lines or 'N/A'}\n\n"
        f"The tree search adds **{delta:+.1f} points** of value over raw "
        "rollout policy decisions."
    )


def _section_qvalue_convergence(data: Dict[str, Any]) -> str:
    summary = data.get("summary", {})
    move_changes = summary.get("move_changes", [])
    total_states = summary.get("total_states", 0)

    lines = [
        "## 1.4 — Q-Value Convergence Check\n",
        f"Tested across **{total_states}** sampled states.\n",
        "### Move Identity Stability\n",
        "| Budget Transition | States | Moves Changed | Change Rate |",
        "|-------------------|--------|---------------|-------------|",
    ]
    for mc in move_changes:
        rate = mc.get("change_rate")
        rate_str = f"{rate:.1%}" if rate is not None else "N/A"
        lines.append(
            f"| {mc['from_budget']//1000}K → {mc['to_budget']//1000}K | "
            f"{mc['total_states']} | {mc['moves_changed']} | {rate_str} |"
        )

    per_budget = summary.get("per_budget", {})
    if per_budget:
        lines.extend([
            "",
            "### Q-Value Statistics by Budget",
            "",
            "| Budget | Mean Q | Std Q | Mean Regret Gap | States |",
            "|--------|--------|-------|-----------------|--------|",
        ])
        for budget in sorted(per_budget, key=int):
            entry = per_budget[budget]
            mq = entry.get("mean_best_q")
            sq = entry.get("std_best_q")
            rg = entry.get("mean_regret_gap")
            mq_str = f"{mq:.4f}" if mq is not None else "N/A"
            sq_str = f"{sq:.4f}" if sq is not None else "N/A"
            rg_str = f"{rg:.4f}" if rg is not None else "N/A"
            lines.append(
                f"| {int(budget)//1000}K | "
                f"{mq_str} | "
                f"{sq_str} | "
                f"{rg_str} | "
                f"{entry.get('states_measured', 0)} |"
            )

    lines.extend([
        "",
        "![Q-Value Convergence Heatmap](plots/qvalue_convergence_heatmap.png)",
        "",
        "![Q-Value Convergence Per State](plots/qvalue_convergence_per_state.png)",
    ])
    return "\n".join(lines)


def _section_seat_bias(data: Dict[str, Any]) -> str:
    per_seat = data.get("per_seat", {})
    anova = data.get("anova", {})
    pairwise = data.get("pairwise_ks", [])

    lines = [
        "## 1.5 — Seat-Position Bias\n",
        "| Seat | Mean Score | Std | 95% CI | N |",
        "|------|-----------|-----|--------|---|",
    ]
    for seat in sorted(per_seat, key=int):
        s = per_seat[seat]
        lines.append(
            f"| P{seat} | {s['mean']:.1f} | {s['std']:.1f} | "
            f"[{s['ci_95_lower']:.1f}, {s['ci_95_upper']:.1f}] | {s['count']} |"
        )

    f_stat = anova.get("f_statistic", "N/A")
    p_val = anova.get("p_value")
    p_str = f"{p_val:.6f}" if p_val is not None else "N/A"
    lines.extend([
        "",
        f"**ANOVA**: F={f_stat}, p={p_str} ({anova.get('method', 'N/A')})",
    ])

    if p_val is not None and p_val < 0.05:
        lines.append(
            "\n> **Significant seat-position bias detected** (p < 0.05). "
            "Seat assignments should be rotated in all future comparisons."
        )
    elif p_val is not None:
        lines.append(
            "\n> No significant seat-position bias detected (p >= 0.05)."
        )

    if pairwise:
        lines.extend([
            "",
            "### Pairwise KS Tests",
            "",
            "| Pair | KS Stat | p-value |",
            "|------|---------|---------|",
        ])
        for pk in pairwise:
            lines.append(
                f"| P{pk['seat_a']} vs P{pk['seat_b']} | "
                f"{pk['ks_statistic']:.4f} | {pk['p_value']:.6f} |"
            )

    lines.extend(["", "![Seat Bias](plots/seat_bias.png)"])
    return "\n".join(lines)


def _section_key_decisions(results: Dict[str, Any]) -> str:
    return (
        "## Key Decisions This Data Informs\n\n"
        "| Measurement | Decision It Informs | Layer Affected |\n"
        "|-------------|--------------------|-----------------|\n"
        "| Branching factor peak location | Where to focus action reduction | Layer 3 |\n"
        "| Branching factor peak magnitude | How aggressive to prune | Layer 3 |\n"
        "| Utilization ratio shape | Action reduction vs exploration tuning priority | Layer 3, 9 |\n"
        "| Simulation quality gap | Whether to replace rollouts with evaluation | Layer 4 |\n"
        "| Q-value convergence budget | Whether parallelisation helps | Layer 8 |\n"
        "| Convergence-slow turn numbers | Where to focus action reduction | Layer 3 |\n"
        "| Seat-position bias magnitude | Tournament design correction | Layer 0.2 |"
    )


def _section_checklist(results: Dict[str, Any]) -> str:
    bf = results.get("branching_factor", {})
    ie = results.get("iteration_efficiency", {})
    sq = results.get("simulation_quality", {})
    qv = results.get("qvalue_convergence", {})
    sb = results.get("seat_bias", {})

    def _check(condition: bool) -> str:
        return "[x]" if condition else "[ ]"

    selfplay_games = sq.get("mcts_num_games", 0)
    heuristic_games = sq.get("heuristic_num_games", 0)
    convergence_states = qv.get("summary", {}).get("total_states", 0)

    return (
        "## Checklist: Layer 1 Complete When...\n\n"
        f"- {_check(selfplay_games >= 500)} 500+ self-play games completed with full logging\n"
        f"- {_check(bool(bf.get('curve')))} Branching factor curve plotted and peak identified\n"
        f"- {_check(bool(ie.get('summary')))} Iteration efficiency curve plotted with threshold annotations\n"
        f"- {_check(heuristic_games >= 100)} Simulation quality audit completed ({heuristic_games} rollout-only games)\n"
        f"- {_check(convergence_states >= 50)} Q-value convergence check completed across {convergence_states} states\n"
        f"- {_check(bool(sb.get('anova')))} Seat-position bias quantified with significance testing\n"
        f"- {_check(selfplay_games >= 500)} All results documented in baseline report"
    )

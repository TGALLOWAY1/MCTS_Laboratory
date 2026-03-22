"""1.3 — Simulation Quality Audit.

Compares the performance of the rollout (heuristic) policy alone against
the full MCTS agent. The gap between scores quantifies how much signal
the tree search adds beyond the rollout evaluations.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from analytics.tournament.arena_stats import load_games_jsonl


def _all_agent_scores(games: List[Dict[str, Any]]) -> List[int]:
    """Extract all individual agent scores from game records."""
    scores: List[int] = []
    for game in games:
        for score in game.get("agent_scores", {}).values():
            scores.append(int(score))
    return scores


def _rank_distribution(games: List[Dict[str, Any]]) -> Dict[int, int]:
    """Compute how often each rank (1st–4th) was achieved across all agents.

    In self-play with identical agents, every agent's rank matters equally.
    """
    counter: Counter[int] = Counter()
    for game in games:
        ranks = game.get("final_ranks", game.get("agent_ranks", {}))
        for rank in ranks.values():
            counter[int(rank)] += 1
    return dict(sorted(counter.items()))


def compute_simulation_quality(
    heuristic_games_path: str | Path,
    mcts_games_path: str | Path,
) -> Dict[str, Any]:
    """Compare heuristic-only scores vs full MCTS scores.

    Args:
        heuristic_games_path: Path to ``games.jsonl`` from heuristic-only run.
        mcts_games_path: Path to ``games.jsonl`` from MCTS self-play run.

    Returns:
        Dict with heuristic/MCTS avg scores, delta, and rank distribution.
    """
    heuristic_games = load_games_jsonl(heuristic_games_path)
    mcts_games = load_games_jsonl(mcts_games_path)

    h_scores = _all_agent_scores(heuristic_games)
    m_scores = _all_agent_scores(mcts_games)

    h_avg = sum(h_scores) / len(h_scores) if h_scores else 0.0
    m_avg = sum(m_scores) / len(m_scores) if m_scores else 0.0

    h_rank_dist = _rank_distribution(heuristic_games)
    m_rank_dist = _rank_distribution(mcts_games)

    return {
        "heuristic_avg_score": round(h_avg, 2),
        "mcts_avg_score": round(m_avg, 2),
        "delta": round(m_avg - h_avg, 2),
        "heuristic_num_games": len(heuristic_games),
        "mcts_num_games": len(mcts_games),
        "heuristic_rank_distribution": h_rank_dist,
        "mcts_rank_distribution": m_rank_dist,
        "heuristic_score_count": len(h_scores),
        "mcts_score_count": len(m_scores),
    }


def format_simulation_quality_table(result: Dict[str, Any]) -> str:
    """Format the simulation quality audit as a readable markdown table."""
    lines = [
        "| Metric | Heuristic-only | Full MCTS | Delta |",
        "|--------|---------------|-----------|-------|",
        f"| Avg Score | {result['heuristic_avg_score']:.1f} | "
        f"{result['mcts_avg_score']:.1f} | "
        f"{result['delta']:+.1f} |",
        f"| Games | {result['heuristic_num_games']} | "
        f"{result['mcts_num_games']} | — |",
        "",
        "**Heuristic-only Rank Distribution:**",
        "",
        "| Rank | Count |",
        "|------|-------|",
    ]
    for rank in sorted(result.get("heuristic_rank_distribution", {})):
        count = result["heuristic_rank_distribution"][rank]
        lines.append(f"| {rank} | {count} |")
    return "\n".join(lines)

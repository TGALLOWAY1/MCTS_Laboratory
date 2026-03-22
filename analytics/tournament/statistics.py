"""Statistical testing utilities for tournament analysis.

Provides bootstrap confidence intervals, paired permutation tests,
per-seat-position analysis, and score margin statistics.

All resampling operates at the game level (not individual player outcomes)
to respect within-game correlation.
"""

import math
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple


def bootstrap_score_ci(
    scores_a: Sequence[float],
    scores_b: Sequence[float],
    n_resamples: int = 10000,
    ci: float = 0.95,
    seed: Optional[int] = None,
) -> Dict[str, float]:
    """Bootstrap confidence interval for the mean score difference (A - B).

    Resamples paired game results to compute a CI for the difference
    in mean scores between two agents.

    Args:
        scores_a: Per-game scores for agent A.
        scores_b: Per-game scores for agent B (same length, paired by game).
        n_resamples: Number of bootstrap resamples.
        ci: Confidence level (e.g. 0.95 for 95% CI).
        seed: Random seed for reproducibility.

    Returns:
        Dict with 'mean_diff', 'ci_lower', 'ci_upper', 'ci_level'.
    """
    if len(scores_a) != len(scores_b):
        raise ValueError("Score lists must be the same length (paired by game).")
    n = len(scores_a)
    if n == 0:
        return {"mean_diff": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "ci_level": ci}

    rng = random.Random(seed)
    diffs = [a - b for a, b in zip(scores_a, scores_b)]
    observed_mean = sum(diffs) / n

    bootstrap_means = []
    for _ in range(n_resamples):
        sample = [diffs[rng.randint(0, n - 1)] for _ in range(n)]
        bootstrap_means.append(sum(sample) / n)

    bootstrap_means.sort()
    alpha = 1.0 - ci
    lo_idx = max(0, int(math.floor(alpha / 2 * n_resamples)))
    hi_idx = min(n_resamples - 1, int(math.ceil((1 - alpha / 2) * n_resamples)))

    return {
        "mean_diff": observed_mean,
        "ci_lower": bootstrap_means[lo_idx],
        "ci_upper": bootstrap_means[hi_idx],
        "ci_level": ci,
    }


def paired_permutation_test(
    game_results: Sequence[Dict[str, Any]],
    agent_a: str,
    agent_b: str,
    n_permutations: int = 10000,
    seed: Optional[int] = None,
) -> Dict[str, float]:
    """Paired permutation test for score difference between two agents.

    Resamples complete games (not individual player outcomes) to
    respect within-game correlation.

    Args:
        game_results: List of game records with 'agent_scores' dict.
        agent_a: First agent name.
        agent_b: Second agent name.
        n_permutations: Number of permutations.
        seed: Random seed for reproducibility.

    Returns:
        Dict with 'observed_diff', 'p_value', 'n_games'.
    """
    rng = random.Random(seed)

    # Extract paired scores from games where both agents played
    diffs = []
    for game in game_results:
        agent_scores = game.get("agent_scores", {})
        if agent_a in agent_scores and agent_b in agent_scores:
            diffs.append(agent_scores[agent_a] - agent_scores[agent_b])

    n = len(diffs)
    if n == 0:
        return {"observed_diff": 0.0, "p_value": 1.0, "n_games": 0}

    observed_diff = sum(diffs) / n

    # Count how many permuted diffs are as extreme as observed
    extreme_count = 0
    for _ in range(n_permutations):
        perm_diffs = [d * (1 if rng.random() < 0.5 else -1) for d in diffs]
        perm_mean = sum(perm_diffs) / n
        if abs(perm_mean) >= abs(observed_diff):
            extreme_count += 1

    p_value = extreme_count / n_permutations

    return {
        "observed_diff": observed_diff,
        "p_value": p_value,
        "n_games": n,
    }


def score_by_seat_position(
    game_results: Sequence[Dict[str, Any]],
    agent_names: Optional[Sequence[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Compute score distribution per seat position for each agent.

    Blokus has a first-player advantage; this analysis helps
    disentangle agent strength from seat-position luck.

    Args:
        game_results: List of game records with 'seat_assignment' and
            'final_scores' dicts.
        agent_names: Optional filter to specific agents.

    Returns:
        Dict[agent_name] -> Dict[seat_position] -> {mean, std, n, scores}
    """
    # Collect scores by agent and seat
    agent_seat_scores: Dict[str, Dict[str, List[float]]] = {}

    for game in game_results:
        seat_assignment = game.get("seat_assignment", {})
        final_scores = game.get("final_scores", {})

        for player_id, agent_name in seat_assignment.items():
            if agent_names and agent_name not in agent_names:
                continue

            score = final_scores.get(str(player_id))
            if score is None:
                continue

            if agent_name not in agent_seat_scores:
                agent_seat_scores[agent_name] = {}
            seat_key = f"P{player_id}"
            if seat_key not in agent_seat_scores[agent_name]:
                agent_seat_scores[agent_name][seat_key] = []
            agent_seat_scores[agent_name][seat_key].append(float(score))

    # Compute summary stats
    result: Dict[str, Dict[str, Any]] = {}
    for agent_name, seats in agent_seat_scores.items():
        result[agent_name] = {}
        for seat, scores in sorted(seats.items()):
            n = len(scores)
            mean = sum(scores) / n if n > 0 else 0.0
            if n > 1:
                variance = sum((s - mean) ** 2 for s in scores) / (n - 1)
                std = math.sqrt(variance)
                se = std / math.sqrt(n)
            else:
                std = 0.0
                se = 0.0
            result[agent_name][seat] = {
                "mean": round(mean, 2),
                "std": round(std, 2),
                "se": round(se, 2),
                "n": n,
            }
    return result


def score_margin_stats(
    game_results: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute score margin statistics across games.

    Score margin = gap between winner's score and last-place score.
    Tight margin = competitive game; blowout = strength mismatch.

    Args:
        game_results: List of game records with 'final_scores' dict.

    Returns:
        Dict with 'mean_margin', 'median_margin', 'std_margin',
        'min_margin', 'max_margin', 'n_games'.
    """
    margins = []
    for game in game_results:
        scores = game.get("final_scores", {})
        if not scores:
            continue
        values = [int(v) for v in scores.values()]
        margin = max(values) - min(values)
        margins.append(float(margin))

    if not margins:
        return {
            "mean_margin": 0.0,
            "median_margin": 0.0,
            "std_margin": 0.0,
            "min_margin": 0.0,
            "max_margin": 0.0,
            "n_games": 0,
        }

    n = len(margins)
    mean = sum(margins) / n
    sorted_m = sorted(margins)
    median = sorted_m[n // 2] if n % 2 == 1 else (sorted_m[n // 2 - 1] + sorted_m[n // 2]) / 2
    variance = sum((m - mean) ** 2 for m in margins) / n if n > 0 else 0.0

    return {
        "mean_margin": round(mean, 2),
        "median_margin": round(median, 2),
        "std_margin": round(math.sqrt(variance), 2),
        "min_margin": round(min(margins), 2),
        "max_margin": round(max(margins), 2),
        "n_games": n,
    }

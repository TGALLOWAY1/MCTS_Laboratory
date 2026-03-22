"""Shared MCTS utility functions."""

import math
from typing import List


def compute_policy_entropy(visits: List[int]) -> float:
    """Compute Shannon entropy over a visit count distribution.

    High entropy = visits spread uniformly (search confused or under-budgeted).
    Low entropy = strong convictions (search converged on a few moves).

    Args:
        visits: List of visit counts for each child of the root.

    Returns:
        Shannon entropy in nats (natural log).
    """
    total = sum(visits)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for v in visits:
        if v > 0:
            p = v / total
            entropy -= p * math.log(p)
    return entropy

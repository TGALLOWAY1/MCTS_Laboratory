"""Adaptive per-move budget selection for human challenge mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional


@dataclass(frozen=True)
class BudgetSignals:
    legal_move_count: int
    board_occupancy: float
    score_deficit: int
    score_rank: int
    regret_gap: Optional[float] = None
    visit_entropy: Optional[float] = None
    best_move_stability: Optional[float] = None


@dataclass(frozen=True)
class BudgetDecision:
    tier: str
    budget_cap_ms: int
    reasons: List[str]
    early_stop_reason: Optional[str] = None


class AdaptiveBudgetController:
    """Deterministic tier selector for challenge-mode MCTS thinking time."""

    REQUIRED_TIERS = ("trivial", "normal", "critical")

    def __init__(
        self,
        *,
        tier_budgets_ms: Mapping[str, int],
        max_budget_ms: int,
    ) -> None:
        missing = [tier for tier in self.REQUIRED_TIERS if tier not in tier_budgets_ms]
        if missing:
            raise ValueError(f"Missing budget tier(s): {', '.join(missing)}")
        self.tier_budgets_ms: Dict[str, int] = {
            tier: min(int(tier_budgets_ms[tier]), int(max_budget_ms))
            for tier in self.REQUIRED_TIERS
        }
        self.max_budget_ms = int(max_budget_ms)

    def choose_budget(self, signals: BudgetSignals) -> BudgetDecision:
        reasons: List[str] = []

        if signals.legal_move_count <= 1:
            return self._decision("trivial", ["one_legal_move"], "one_legal_move")

        if signals.legal_move_count <= 6:
            reasons.append("low_branching")

        high_branching = signals.legal_move_count >= 160
        if high_branching:
            reasons.append("high_branching")

        close_q = signals.regret_gap is not None and signals.regret_gap <= 0.05
        if close_q:
            reasons.append("close_q_margin")

        confident_q = signals.regret_gap is not None and signals.regret_gap >= 0.25

        high_entropy = signals.visit_entropy is not None and signals.visit_entropy >= 0.75
        if high_entropy:
            reasons.append("high_visit_entropy")

        low_entropy = signals.visit_entropy is not None and signals.visit_entropy <= 0.35

        unstable = signals.best_move_stability is not None and signals.best_move_stability <= 0.5
        if unstable:
            reasons.append("unstable_best_move")

        stable = signals.best_move_stability is not None and signals.best_move_stability >= 0.75
        if stable:
            reasons.append("stable_best_move")

        late_game = signals.board_occupancy >= 0.55
        if late_game:
            reasons.append("late_game")

        behind = signals.score_deficit >= 8 or signals.score_rank >= 3
        if behind:
            reasons.append("behind")

        uncertainty_count = sum(1 for value in (close_q, high_entropy, unstable) if value)
        tactical_pressure = late_game or behind
        if (close_q and high_entropy) or (uncertainty_count >= 2 and tactical_pressure):
            return self._decision("critical", reasons)

        if reasons == ["low_branching"]:
            return self._decision("trivial", reasons, "low_branching")

        if confident_q and low_entropy and stable and not high_branching:
            return self._decision("trivial", reasons, "stable_best_move")

        if not reasons:
            reasons.append("ordinary_position")

        return self._decision("normal", reasons)

    def _decision(
        self,
        tier: str,
        reasons: List[str],
        early_stop_reason: Optional[str] = None,
    ) -> BudgetDecision:
        return BudgetDecision(
            tier=tier,
            budget_cap_ms=self.tier_budgets_ms[tier],
            reasons=list(reasons),
            early_stop_reason=early_stop_reason,
        )

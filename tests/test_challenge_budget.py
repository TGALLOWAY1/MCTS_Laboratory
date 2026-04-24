from mcts.adaptive_budget import AdaptiveBudgetController, BudgetSignals


def _controller() -> AdaptiveBudgetController:
    return AdaptiveBudgetController(
        tier_budgets_ms={"trivial": 1000, "normal": 5000, "critical": 30000},
        max_budget_ms=30000,
    )


def test_one_legal_move_is_trivial_with_reason():
    decision = _controller().choose_budget(
        BudgetSignals(
            legal_move_count=1,
            board_occupancy=0.2,
            score_deficit=0,
            score_rank=1,
        )
    )

    assert decision.tier == "trivial"
    assert decision.budget_cap_ms == 1000
    assert decision.early_stop_reason == "one_legal_move"
    assert "one_legal_move" in decision.reasons


def test_confident_warmup_does_not_escalate_to_critical():
    decision = _controller().choose_budget(
        BudgetSignals(
            legal_move_count=80,
            board_occupancy=0.3,
            score_deficit=0,
            score_rank=1,
            regret_gap=0.4,
            visit_entropy=0.15,
            best_move_stability=1.0,
        )
    )

    assert decision.tier in {"trivial", "normal"}
    assert decision.tier != "critical"
    assert "stable_best_move" in decision.reasons


def test_uncertain_warmup_escalates_to_critical():
    decision = _controller().choose_budget(
        BudgetSignals(
            legal_move_count=70,
            board_occupancy=0.58,
            score_deficit=9,
            score_rank=3,
            regret_gap=0.03,
            visit_entropy=0.92,
            best_move_stability=0.25,
        )
    )

    assert decision.tier == "critical"
    assert decision.budget_cap_ms == 30000
    assert "close_q_margin" in decision.reasons
    assert "high_visit_entropy" in decision.reasons


def test_high_branching_alone_stays_normal():
    decision = _controller().choose_budget(
        BudgetSignals(
            legal_move_count=240,
            board_occupancy=0.18,
            score_deficit=0,
            score_rank=1,
            regret_gap=0.35,
            visit_entropy=0.25,
            best_move_stability=1.0,
        )
    )

    assert decision.tier == "normal"
    assert decision.budget_cap_ms == 5000
    assert "high_branching" in decision.reasons


def test_budget_decision_is_deterministic():
    signals = BudgetSignals(
        legal_move_count=64,
        board_occupancy=0.6,
        score_deficit=5,
        score_rank=2,
        regret_gap=0.04,
        visit_entropy=0.8,
        best_move_stability=0.4,
    )

    first = _controller().choose_budget(signals)
    second = _controller().choose_budget(signals)

    assert first == second

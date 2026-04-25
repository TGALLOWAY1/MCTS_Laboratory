import sys
import types

from engine.board import Board, Player
from engine.move_generator import LegalMoveGenerator
from mcts.champion_profile import (
    CHALLENGE_CHAMPION_PROFILE,
    build_mcts_kwargs,
    load_challenge_champion_profile,
)
from schemas.game_state import AgentType
from webapi.gameplay_agent_factory import build_deploy_gameplay_agent


class _DummyPlackettLuce:
    def __init__(self, *args, **kwargs):
        pass

    def rating(self):
        return types.SimpleNamespace(mu=25.0, sigma=25.0 / 3.0)

    def rate(self, teams):
        return teams


openskill_module = types.ModuleType("openskill")
openskill_models_module = types.ModuleType("openskill.models")
openskill_models_module.PlackettLuce = _DummyPlackettLuce
sys.modules.setdefault("openskill", openskill_module)
sys.modules.setdefault("openskill.models", openskill_models_module)

from analytics.tournament.arena_runner import AgentConfig, build_agent


def test_challenge_profile_contains_validated_non_learned_stack():
    profile = load_challenge_champion_profile()
    kwargs = build_mcts_kwargs(profile)

    assert profile["profile"] == CHALLENGE_CHAMPION_PROFILE
    assert profile["max_budget_ms"] == 30000
    assert profile["warmup_budget_ms"] == 750
    assert profile["tier_budgets_ms"] == {
        "trivial": 1000,
        "normal": 5000,
        "critical": 30000,
    }
    assert kwargs["rollout_policy"] == "random"
    assert kwargs["rollout_cutoff_depth"] == 5
    assert kwargs["minimax_backup_alpha"] == 0.25
    assert kwargs["rave_enabled"] is True
    assert kwargs["rave_k"] == 1000
    assert kwargs["progressive_widening_enabled"] is True
    assert kwargs["pw_c"] == 2.0
    assert kwargs["pw_alpha"] == 0.5
    assert kwargs["adaptive_rollout_depth_enabled"] is True
    assert kwargs["adaptive_exploration_enabled"] is False
    assert kwargs["sufficiency_threshold_enabled"] is False
    assert kwargs["loss_avoidance_enabled"] is False
    assert kwargs["state_eval_weights"]["opponent_avg_mobility"] == -0.3


def test_deploy_factory_uses_challenge_profile_for_full_mcts_agent():
    adapter = build_deploy_gameplay_agent(
        AgentType.MCTS,
        {"profile": CHALLENGE_CHAMPION_PROFILE, "seed": 123},
    )

    agent = adapter._agent
    assert adapter.profile_name == CHALLENGE_CHAMPION_PROFILE
    assert agent.rave_enabled is True
    assert agent.progressive_widening_enabled is True
    assert agent.rollout_policy == "random"
    assert agent.rollout_cutoff_depth == 5
    assert agent.adaptive_rollout_depth_enabled is True


def test_challenge_adapter_emits_budget_and_search_stats():
    adapter = build_deploy_gameplay_agent(
        AgentType.MCTS,
        {
            "profile": CHALLENGE_CHAMPION_PROFILE,
            "seed": 123,
            "max_budget_ms": 1000,
            "tier_budgets_ms": {"trivial": 50, "normal": 50, "critical": 50},
            "warmup_budget_ms": 25,
        },
    )
    board = Board()
    legal_moves = LegalMoveGenerator().get_legal_moves(board, Player.RED)

    move, stats = adapter.choose_move(board, Player.RED, legal_moves[:1], 1000)

    assert move == legal_moves[0]
    assert stats["budgetTier"] == "trivial"
    assert stats["budgetCapMs"] == 50
    assert stats["earlyStopReason"] == "one_legal_move"
    assert stats["timeBudgetMs"] == 50
    assert "timeSpentMs" in stats
    assert "nodesEvaluated" in stats
    assert "iterations_run" in stats
    assert "budgetReasons" in stats


def test_arena_agent_config_can_use_challenge_profile():
    adapter = build_agent(
        AgentConfig(
            name="ChallengeChampion",
            type="mcts",
            thinking_time_ms=200,
            params={"profile": CHALLENGE_CHAMPION_PROFILE},
        ),
        seed=123,
    )

    agent = adapter.agent
    assert agent.rave_enabled is True
    assert agent.progressive_widening_enabled is True
    assert agent.rollout_policy == "random"
    assert agent.rollout_cutoff_depth == 5


def test_arena_agent_config_can_use_challenge_gameplay_adapter():
    adapter = build_agent(
        AgentConfig(
            name="ChallengeChampionGameplay",
            type="challenge_champion_gameplay",
            thinking_time_ms=200,
            params={
                "profile": CHALLENGE_CHAMPION_PROFILE,
                "max_budget_ms": 1000,
                "warmup_budget_ms": 25,
                "tier_budgets_ms": {"trivial": 50, "normal": 100, "critical": 200},
                "seed": 321,
            },
        ),
        seed=123,
    )

    board = Board()
    legal_moves = LegalMoveGenerator().get_legal_moves(board, Player.RED)
    move, stats = adapter.play_turn(board, Player.RED, legal_moves, 200)

    assert move is not None
    legal_signatures = {
        (candidate.piece_id, candidate.orientation, candidate.anchor_row, candidate.anchor_col)
        for candidate in legal_moves
    }
    move_signature = (move.piece_id, move.orientation, move.anchor_row, move.anchor_col)
    assert move_signature in legal_signatures
    assert "budgetTier" in stats
    assert "budgetCapMs" in stats
    assert "budgetReasons" in stats
    assert stats["timeBudgetMs"] <= 200

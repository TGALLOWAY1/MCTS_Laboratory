"""Tests for TrueSkill rating system and statistical utilities."""

import random

import pytest

from analytics.tournament.statistics import (
    bootstrap_score_ci,
    paired_permutation_test,
    score_by_seat_position,
    score_margin_stats,
)
from analytics.tournament.trueskill_rating import TrueSkillTracker


class TestTrueSkillTracker:
    """Tests for the TrueSkillTracker class."""

    def test_initial_rating(self):
        tracker = TrueSkillTracker()
        rating = tracker.get_rating("agent_a")
        assert rating["mu"] == pytest.approx(25.0, abs=0.01)
        assert rating["sigma"] == pytest.approx(25.0 / 3, abs=0.01)
        assert rating["games_played"] == 0

    def test_single_game_updates_ratings(self):
        tracker = TrueSkillTracker()
        tracker.update_game({"winner": 80, "loser": 20})
        w = tracker.get_rating("winner")
        l = tracker.get_rating("loser")
        assert w["mu"] > l["mu"]
        assert w["games_played"] == 1
        assert l["games_played"] == 1

    def test_four_player_ranking_order(self):
        """After many games with consistent rankings, leaderboard should match."""
        tracker = TrueSkillTracker()
        rng = random.Random(42)
        for _ in range(50):
            tracker.update_game({
                "strong": 70 + rng.randint(-5, 5),
                "medium": 50 + rng.randint(-5, 5),
                "weak": 30 + rng.randint(-5, 5),
                "terrible": 10 + rng.randint(-5, 5),
            })
        lb = tracker.get_leaderboard()
        names_ordered = [e["agent_id"] for e in lb]
        assert names_ordered == ["strong", "medium", "weak", "terrible"]

    def test_conservative_estimate_ordering(self):
        """Conservative estimates (mu - 3*sigma) should be properly ordered."""
        tracker = TrueSkillTracker()
        rng = random.Random(123)
        for _ in range(100):
            tracker.update_game({
                "a": 80 + rng.randint(-10, 10),
                "b": 60 + rng.randint(-10, 10),
                "c": 40 + rng.randint(-10, 10),
                "d": 20 + rng.randint(-10, 10),
            })
        lb = tracker.get_leaderboard()
        conserv = [e["conservative"] for e in lb]
        # Conservative estimates should be strictly decreasing
        for i in range(len(conserv) - 1):
            assert conserv[i] > conserv[i + 1]

    def test_convergence_detection(self):
        """After enough games, sigma should decrease and convergence detected."""
        tracker = TrueSkillTracker()
        # Initially not converged with tight threshold
        tracker._ensure_agent("a")
        assert not tracker.is_converged(sigma_threshold=5.0)  # sigma starts at ~8.33
        # But converged with loose threshold
        assert tracker.is_converged(sigma_threshold=9.0)  # Initial sigma ~8.33 < 9.0

    def test_reset_agent_increases_sigma(self):
        """reset_agent with increase_sigma=True should reset sigma but keep mu."""
        tracker = TrueSkillTracker()
        # Play some games to change mu
        for _ in range(20):
            tracker.update_game({"target": 80, "other": 20})
        r_before = tracker.get_rating("target")
        assert r_before["mu"] > 25.0  # mu should have increased

        tracker.reset_agent("target", increase_sigma=True)
        r_after = tracker.get_rating("target")
        assert r_after["mu"] == pytest.approx(r_before["mu"], abs=0.01)
        assert r_after["sigma"] == pytest.approx(25.0 / 3, abs=0.01)

    def test_reset_agent_full_reset(self):
        """reset_agent with increase_sigma=False should fully reset."""
        tracker = TrueSkillTracker()
        for _ in range(20):
            tracker.update_game({"target": 80, "other": 20})
        tracker.reset_agent("target", increase_sigma=False)
        r = tracker.get_rating("target")
        assert r["mu"] == pytest.approx(25.0, abs=0.01)
        assert r["games_played"] == 0

    def test_leaderboard_has_rank(self):
        tracker = TrueSkillTracker()
        tracker.update_game({"a": 80, "b": 60, "c": 40, "d": 20})
        lb = tracker.get_leaderboard()
        ranks = [e["rank"] for e in lb]
        assert ranks == [1, 2, 3, 4]

    def test_agent_ids_property(self):
        tracker = TrueSkillTracker()
        tracker.update_game({"x": 50, "y": 40})
        assert set(tracker.agent_ids) == {"x", "y"}

    def test_get_ratings_all_agents(self):
        tracker = TrueSkillTracker()
        tracker.update_game({"a": 1, "b": 2, "c": 3})
        ratings = tracker.get_ratings()
        assert set(ratings.keys()) == {"a", "b", "c"}
        for agent_id, info in ratings.items():
            assert "mu" in info
            assert "sigma" in info
            assert "conservative" in info


class TestStatisticalUtilities:
    """Tests for bootstrap CI, permutation test, seat analysis, margins."""

    def test_bootstrap_score_ci_basic(self):
        # Agent A always scores 10 more than B
        ci = bootstrap_score_ci(
            [60, 70, 65, 55, 80],
            [50, 60, 55, 45, 70],
            n_resamples=5000,
            seed=42,
        )
        assert ci["mean_diff"] == 10.0
        assert ci["ci_lower"] > 0  # A is consistently better
        assert ci["ci_upper"] > 0
        assert ci["ci_level"] == 0.95

    def test_bootstrap_empty_inputs(self):
        ci = bootstrap_score_ci([], [], seed=1)
        assert ci["mean_diff"] == 0.0

    def test_bootstrap_equal_scores(self):
        ci = bootstrap_score_ci([50, 50, 50], [50, 50, 50], seed=1)
        assert ci["mean_diff"] == 0.0
        assert ci["ci_lower"] == 0.0
        assert ci["ci_upper"] == 0.0

    def test_paired_permutation_test_significant(self):
        # A always beats B
        games = [
            {"agent_scores": {"A": 80, "B": 40}} for _ in range(20)
        ]
        result = paired_permutation_test(games, "A", "B", seed=42)
        assert result["observed_diff"] == 40.0
        assert result["p_value"] < 0.01  # Highly significant
        assert result["n_games"] == 20

    def test_paired_permutation_test_no_games(self):
        result = paired_permutation_test([], "A", "B", seed=42)
        assert result["p_value"] == 1.0
        assert result["n_games"] == 0

    def test_score_by_seat_position(self):
        games = [
            {
                "seat_assignment": {"1": "Agent1", "2": "Agent2", "3": "Agent1", "4": "Agent2"},
                "final_scores": {"1": 60, "2": 50, "3": 40, "4": 30},
            }
        ]
        result = score_by_seat_position(games)
        assert "Agent1" in result
        assert "Agent2" in result

    def test_score_margin_stats(self):
        games = [
            {"final_scores": {"1": 80, "2": 60, "3": 40, "4": 20}},
            {"final_scores": {"1": 50, "2": 48, "3": 46, "4": 44}},
        ]
        result = score_margin_stats(games)
        assert result["n_games"] == 2
        assert result["mean_margin"] == 33.0  # (60 + 6) / 2
        assert result["min_margin"] == 6.0
        assert result["max_margin"] == 60.0

    def test_score_margin_empty(self):
        result = score_margin_stats([])
        assert result["n_games"] == 0

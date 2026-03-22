"""Tests for Layer 1 baseline analysis modules."""

import math
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.baseline.branching_factor import (
    compute_branching_factor_curve,
    find_peak,
    plot_branching_factor_curve,
)
from analytics.baseline.iteration_efficiency import (
    compute_utilization_curve,
    plot_utilization_curve,
    summarize_utilization,
)
from analytics.baseline.seat_bias import compute_seat_bias, plot_seat_bias
from analytics.baseline.simulation_quality import compute_simulation_quality
from analytics.baseline.report import generate_baseline_report


# ---- Fixtures ----


def _make_steps(n_games=3, turns_per_game=20):
    """Generate synthetic step log entries."""
    steps = []
    for g in range(n_games):
        game_id = f"game_{g:04d}"
        for t in range(1, turns_per_game + 1):
            bf = max(1, 50 + 30 * math.sin(t * 0.3) + g * 2)
            iterations = 2000
            best_visits = int(iterations * (0.3 + 0.4 * (t / turns_per_game)))
            steps.append(
                {
                    "game_id": game_id,
                    "turn_index": t,
                    "player_id": (t % 4) + 1,
                    "legal_moves_before": int(bf),
                    "legal_moves_after": int(bf) - 1,
                    "action": {
                        "piece_id": max(1, 21 - t),
                        "orientation": 0,
                        "anchor_row": t,
                        "anchor_col": t,
                    },
                    "mcts_diagnostics": {
                        "branching_factor": int(bf),
                        "iterations": iterations,
                        "best_move_visits": best_visits,
                        "best_move_q": 0.5 + 0.01 * t,
                        "second_best_q": 0.5 + 0.005 * t,
                        "regret_gap": 0.005 * t,
                        "visit_entropy": 2.0 - 0.05 * t,
                        "tree_size": 1000 + t * 10,
                        "tree_depth_max": 5 + t // 4,
                    },
                    "metrics": {},
                }
            )
    return steps


def _make_games(n_games=10):
    """Generate synthetic game records."""
    games = []
    for g in range(n_games):
        scores = {
            "1": 40 + g % 5,
            "2": 38 + g % 3,
            "3": 35 + g % 7,
            "4": 33 + g % 4,
        }
        winner_id = max(scores, key=lambda k: scores[k])
        games.append(
            {
                "game_id": f"game_{g:04d}",
                "game_index": g,
                "seat_assignment": {"1": "agent_a", "2": "agent_b", "3": "agent_c", "4": "agent_d"},
                "final_scores": scores,
                "final_ranks": {"1": 1, "2": 2, "3": 3, "4": 4},
                "agent_scores": {"agent_a": scores["1"], "agent_b": scores["2"],
                                 "agent_c": scores["3"], "agent_d": scores["4"]},
                "agent_ranks": {"agent_a": 1, "agent_b": 2, "agent_c": 3, "agent_d": 4},
                "winner_ids": [int(winner_id)],
                "winner_agents": ["agent_a"],
                "winner_id": int(winner_id),
                "moves_made": 80,
                "turn_count": 80,
            }
        )
    return games


# ---- 1.1 Branching Factor ----


class TestBranchingFactor:
    def test_compute_curve(self):
        steps = _make_steps()
        curve = compute_branching_factor_curve(steps)
        assert len(curve) > 0
        for turn, stats in curve.items():
            assert "mean" in stats
            assert "std" in stats
            assert stats["count"] > 0

    def test_find_peak(self):
        steps = _make_steps()
        curve = compute_branching_factor_curve(steps)
        peak = find_peak(curve, iteration_budget=2000)
        assert peak["peak_turn"] is not None
        assert peak["peak_bf"] > 0
        assert peak["implied_visits_per_child"] > 0

    def test_find_peak_empty(self):
        peak = find_peak({}, iteration_budget=2000)
        assert peak["peak_turn"] is None

    def test_plot(self):
        steps = _make_steps()
        curve = compute_branching_factor_curve(steps)
        peak = find_peak(curve)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bf.png"
            plot_branching_factor_curve(curve, peak, path)
            assert path.exists()
            assert path.stat().st_size > 0


# ---- 1.2 Iteration Efficiency ----


class TestIterationEfficiency:
    def test_compute_curve(self):
        steps = _make_steps()
        curve = compute_utilization_curve(steps)
        assert len(curve) > 0
        for turn, stats in curve.items():
            assert 0 <= stats["mean"] <= 1

    def test_summarize(self):
        steps = _make_steps()
        curve = compute_utilization_curve(steps)
        summary = summarize_utilization(curve)
        assert summary["total_turns"] > 0
        assert summary["overall_mean"] is not None

    def test_plot(self):
        steps = _make_steps()
        curve = compute_utilization_curve(steps)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "util.png"
            plot_utilization_curve(curve, path)
            assert path.exists()


# ---- 1.3 Simulation Quality ----


class TestSimulationQuality:
    def test_compute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            h_path = Path(tmpdir) / "heuristic_games.jsonl"
            m_path = Path(tmpdir) / "mcts_games.jsonl"
            import json

            h_games = _make_games(5)
            m_games = _make_games(5)
            # Make MCTS scores slightly higher
            for g in m_games:
                for k in g["final_scores"]:
                    g["final_scores"][k] += 5
                for k in g["agent_scores"]:
                    g["agent_scores"][k] += 5

            with h_path.open("w") as f:
                for g in h_games:
                    f.write(json.dumps(g) + "\n")
            with m_path.open("w") as f:
                for g in m_games:
                    f.write(json.dumps(g) + "\n")

            result = compute_simulation_quality(h_path, m_path)
            assert result["delta"] > 0
            assert result["heuristic_num_games"] == 5
            assert result["mcts_num_games"] == 5


# ---- 1.5 Seat Bias ----


class TestSeatBias:
    def test_compute(self):
        games = _make_games(20)
        result = compute_seat_bias(games)
        assert "per_seat" in result
        assert len(result["per_seat"]) == 4
        assert "anova" in result
        for seat_stats in result["per_seat"].values():
            assert "mean" in seat_stats
            assert "ci_95_lower" in seat_stats

    def test_plot(self):
        games = _make_games(20)
        result = compute_seat_bias(games)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "seat.png"
            plot_seat_bias(result, path)
            assert path.exists()


# ---- Report ----


class TestReport:
    def test_generate(self):
        results = {
            "branching_factor": {
                "curve": {1: {"mean": 50, "std": 10, "count": 100, "min": 20, "max": 80}},
                "peak": {"peak_turn": 1, "peak_bf": 50, "implied_visits_per_child": 40, "iteration_budget": 2000},
            },
            "iteration_efficiency": {
                "summary": {"overall_mean": 0.45, "turns_below_50pct": 10, "turns_above_90pct": 2, "total_turns": 20},
            },
            "simulation_quality": {
                "heuristic_avg_score": 35.0,
                "mcts_avg_score": 50.0,
                "delta": 15.0,
                "heuristic_num_games": 100,
                "mcts_num_games": 500,
                "heuristic_rank_distribution": {1: 25, 2: 25, 3: 25, 4: 25},
            },
            "qvalue_convergence": {
                "summary": {"total_states": 50, "move_changes": [], "per_budget": {}},
            },
            "seat_bias": {
                "per_seat": {
                    1: {"mean": 40, "std": 5, "ci_95_lower": 39, "ci_95_upper": 41, "count": 500},
                    2: {"mean": 39, "std": 5, "ci_95_lower": 38, "ci_95_upper": 40, "count": 500},
                    3: {"mean": 38, "std": 5, "ci_95_lower": 37, "ci_95_upper": 39, "count": 500},
                    4: {"mean": 37, "std": 5, "ci_95_lower": 36, "ci_95_upper": 38, "count": 500},
                },
                "anova": {"f_statistic": 3.5, "p_value": 0.015, "method": "test"},
                "pairwise_ks": [],
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.md"
            generate_baseline_report(results, path)
            assert path.exists()
            content = path.read_text()
            assert "1.1" in content
            assert "1.2" in content
            assert "1.3" in content
            assert "1.4" in content
            assert "1.5" in content
            assert "Layer 3" in content  # key decisions table


# ---- State reconstruction ----


class TestStateReconstruction:
    def test_reconstruct_from_real_game(self):
        """Test that we can reconstruct a board state from step actions."""
        from engine.game import BlokusGame
        from engine.move_generator import Move

        game = BlokusGame(enable_telemetry=False)
        legal_moves = game.get_legal_moves(game.board.current_player)
        if not legal_moves:
            pytest.skip("No legal moves at start")

        # Make a move
        move = legal_moves[0]
        player = game.board.current_player
        game.make_move(move, player)

        # Build a synthetic step log entry
        step = {
            "game_id": "test_game",
            "turn_index": 1,
            "player_id": player.value,
            "action": {
                "piece_id": move.piece_id,
                "orientation": move.orientation,
                "anchor_row": move.anchor_row,
                "anchor_col": move.anchor_col,
            },
        }

        # Reconstruct
        from analytics.baseline.qvalue_convergence import reconstruct_board_state

        result = reconstruct_board_state([step], "test_game", target_turn=2)
        # After replaying 1 move, board should have same move count
        if result is not None:
            board, curr_player, legal = result
            assert board.move_count == 1

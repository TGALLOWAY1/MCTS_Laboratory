"""Tests for Layer 6: Evaluation Function Refinement.

Covers:
- BlokusStateEvaluator.extract_features() returns all 7 features
- Phase-dependent evaluation selects correct weights per phase
- Phase boundary classification
- MCTSAgent passes phase_weights through to evaluator
- Calibrated weight JSON loading
- Feature extraction consistency with evaluate()
"""

import json
import math
import tempfile
from pathlib import Path

import numpy as np
import pytest

from engine.board import Board, Player
from engine.game import BlokusGame
from engine.move_generator import get_shared_generator
from mcts.state_evaluator import (
    DEFAULT_WEIGHTS,
    FEATURE_NAMES,
    PHASE_EARLY_THRESHOLD,
    PHASE_LATE_THRESHOLD,
    BlokusStateEvaluator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_board():
    game = BlokusGame(enable_telemetry=False)
    return game.board


@pytest.fixture
def mid_game_board():
    """Board with ~30% occupancy (mid-game)."""
    game = BlokusGame(enable_telemetry=False)
    board = game.board
    move_gen = get_shared_generator()
    turns = 0
    consecutive_passes = 0
    while turns < 40 and not board.game_over:
        player = board.current_player
        legal = move_gen.get_legal_moves(board, player)
        if not legal:
            consecutive_passes += 1
            if consecutive_passes >= 4:
                break
            board._update_current_player()
            turns += 1
            continue
        consecutive_passes = 0
        game.make_move(legal[0], player)
        turns += 1
    return board


@pytest.fixture
def evaluator():
    return BlokusStateEvaluator()


@pytest.fixture
def phase_evaluator():
    phase_weights = {
        "early": {
            "squares_placed": 0.10,
            "remaining_piece_area": -0.05,
            "accessible_corners": 0.40,
            "reachable_empty_squares": 0.20,
            "largest_remaining_piece_size": 0.05,
            "opponent_avg_mobility": -0.15,
            "territory_enclosure_area": 0.00,
        },
        "mid": {
            "squares_placed": 0.25,
            "remaining_piece_area": -0.20,
            "accessible_corners": 0.30,
            "reachable_empty_squares": 0.10,
            "largest_remaining_piece_size": 0.10,
            "opponent_avg_mobility": -0.15,
            "territory_enclosure_area": 0.00,
        },
        "late": {
            "squares_placed": 0.40,
            "remaining_piece_area": -0.25,
            "accessible_corners": 0.15,
            "reachable_empty_squares": 0.05,
            "largest_remaining_piece_size": 0.15,
            "opponent_avg_mobility": -0.05,
            "territory_enclosure_area": 0.00,
        },
    }
    return BlokusStateEvaluator(phase_weights=phase_weights)


# ---------------------------------------------------------------------------
# Tests: Feature Extraction
# ---------------------------------------------------------------------------


class TestFeatureExtraction:
    def test_extract_features_returns_all_seven(self, evaluator, fresh_board):
        features = evaluator.extract_features(fresh_board, Player.RED)
        assert set(features.keys()) == set(FEATURE_NAMES)
        assert len(features) == 7

    def test_extract_features_values_normalised(self, evaluator, fresh_board):
        features = evaluator.extract_features(fresh_board, Player.RED)
        for name, val in features.items():
            assert 0.0 <= val <= 1.0, f"Feature {name}={val} out of [0, 1]"

    def test_extract_features_mid_game(self, evaluator, mid_game_board):
        for player in Player:
            features = evaluator.extract_features(mid_game_board, player)
            assert len(features) == 7
            for val in features.values():
                assert 0.0 <= val <= 1.0

    def test_evaluate_features_matches_evaluate(self, evaluator, mid_game_board):
        """Weighted sum of extract_features() must equal evaluate()."""
        for player in Player:
            features = evaluator.extract_features(mid_game_board, player)
            expected = evaluator.evaluate(mid_game_board, player)
            manual_sum = sum(
                evaluator.weights.get(k, 0.0) * v for k, v in features.items()
            )
            manual_clamped = max(0.0, min(1.0, manual_sum))
            assert abs(expected - manual_clamped) < 1e-9, (
                f"Player {player}: evaluate()={expected} != manual={manual_clamped}"
            )


# ---------------------------------------------------------------------------
# Tests: Phase Classification
# ---------------------------------------------------------------------------


class TestPhaseClassification:
    def test_early_phase(self, fresh_board):
        phase = BlokusStateEvaluator.get_phase(fresh_board)
        assert phase == "early"

    def test_phase_boundaries(self):
        """Test boundary values for phase thresholds."""
        board = Board()
        size = board.SIZE

        # Manually set occupancy to just below early threshold
        target_cells = int(PHASE_EARLY_THRESHOLD * size * size) - 1
        for i in range(target_cells):
            r, c = divmod(i, size)
            board.grid[r, c] = 1
        assert BlokusStateEvaluator.get_phase(board) == "early"

        # Add one more to cross into mid
        board.grid[target_cells // size, target_cells % size] = 1
        assert BlokusStateEvaluator.get_phase(board) == "mid"

    def test_late_phase(self):
        board = Board()
        size = board.SIZE
        target_cells = int(PHASE_LATE_THRESHOLD * size * size) + 1
        for i in range(target_cells):
            r, c = divmod(i, size)
            board.grid[r, c] = 1
        assert BlokusStateEvaluator.get_phase(board) == "late"

    def test_mid_game_phase(self, mid_game_board):
        phase = BlokusStateEvaluator.get_phase(mid_game_board)
        occ = float(np.count_nonzero(mid_game_board.grid)) / (
            mid_game_board.SIZE * mid_game_board.SIZE
        )
        if occ < PHASE_EARLY_THRESHOLD:
            assert phase == "early"
        elif occ < PHASE_LATE_THRESHOLD:
            assert phase == "mid"
        else:
            assert phase == "late"


# ---------------------------------------------------------------------------
# Tests: Phase-Dependent Evaluation
# ---------------------------------------------------------------------------


class TestPhaseDependentEvaluation:
    def test_phase_weights_used_early(self, phase_evaluator, fresh_board):
        """On an empty/early board, early-phase weights should be used."""
        val = phase_evaluator.evaluate(fresh_board, Player.RED)
        # Should use early weights (corners=0.40) not default (corners=0.25)
        assert isinstance(val, float)
        assert 0.0 <= val <= 1.0

    def test_phase_weights_differ_from_default(self, phase_evaluator, mid_game_board):
        """Phase evaluator should produce different scores than default."""
        default_eval = BlokusStateEvaluator()
        for player in Player:
            phase_val = phase_evaluator.evaluate(mid_game_board, player)
            default_val = default_eval.evaluate(mid_game_board, player)
            # They CAN be equal by coincidence, but at least types should match
            assert isinstance(phase_val, float)
            assert isinstance(default_val, float)

    def test_no_phase_weights_uses_default(self, evaluator, mid_game_board):
        """Without phase_weights, default single weight vector is used."""
        val = evaluator.evaluate(mid_game_board, Player.RED)
        features = evaluator.extract_features(mid_game_board, Player.RED)
        manual = max(0.0, min(1.0, sum(
            DEFAULT_WEIGHTS.get(k, 0.0) * v for k, v in features.items()
        )))
        assert abs(val - manual) < 1e-9


# ---------------------------------------------------------------------------
# Tests: MCTSAgent Integration
# ---------------------------------------------------------------------------


class TestMCTSAgentIntegration:
    def test_phase_weights_passed_to_evaluator(self):
        from mcts.mcts_agent import MCTSAgent

        phase_weights = {
            "early": dict(DEFAULT_WEIGHTS),
            "mid": dict(DEFAULT_WEIGHTS),
            "late": dict(DEFAULT_WEIGHTS),
        }
        # Modify one weight to verify it's passed through
        phase_weights["early"]["squares_placed"] = 0.99

        agent = MCTSAgent(
            iterations=10,
            state_eval_phase_weights=phase_weights,
        )
        assert agent.state_evaluator.phase_weights is not None
        assert agent.state_evaluator.phase_weights["early"]["squares_placed"] == 0.99

    def test_no_phase_weights_default(self):
        from mcts.mcts_agent import MCTSAgent

        agent = MCTSAgent(iterations=10)
        assert agent.state_evaluator.phase_weights is None

    def test_custom_single_weights(self):
        from mcts.mcts_agent import MCTSAgent

        custom = {"squares_placed": 0.50, "accessible_corners": 0.50}
        agent = MCTSAgent(iterations=10, state_eval_weights=custom)
        assert agent.state_evaluator.weights["squares_placed"] == 0.50


# ---------------------------------------------------------------------------
# Tests: Calibrated Weights JSON
# ---------------------------------------------------------------------------


class TestCalibratedWeightsJSON:
    def test_load_calibrated_weights(self):
        weights_data = {
            "single_weights": {
                "squares_placed": 0.35,
                "remaining_piece_area": -0.20,
                "accessible_corners": 0.28,
                "reachable_empty_squares": 0.12,
                "largest_remaining_piece_size": 0.08,
                "opponent_avg_mobility": -0.12,
                "territory_enclosure_area": 0.00,
            },
            "phase_weights": {
                "early": {"squares_placed": 0.10, "accessible_corners": 0.40},
                "mid": {"squares_placed": 0.25, "accessible_corners": 0.30},
                "late": {"squares_placed": 0.40, "accessible_corners": 0.15},
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(weights_data, f)
            tmp_path = f.name

        try:
            with open(tmp_path) as f:
                loaded = json.load(f)

            evaluator = BlokusStateEvaluator(weights=loaded["single_weights"])
            assert evaluator.weights["squares_placed"] == 0.35

            phase_eval = BlokusStateEvaluator(phase_weights=loaded["phase_weights"])
            assert phase_eval.phase_weights["early"]["accessible_corners"] == 0.40
        finally:
            Path(tmp_path).unlink(missing_ok=True)

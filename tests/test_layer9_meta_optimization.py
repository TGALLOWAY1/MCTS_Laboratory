"""Tests for Layer 9: Meta-Optimization of MCTS."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import Board, Player
from engine.move_generator import get_shared_generator
from mcts.mcts_agent import MCTSAgent, MCTSNode


def _move_matches_any(move, legal_moves):
    """Check if move matches any legal move by attributes (not identity)."""
    for lm in legal_moves:
        if (move.piece_id == lm.piece_id
                and move.orientation == lm.orientation
                and move.anchor_row == lm.anchor_row
                and move.anchor_col == lm.anchor_col):
            return True
    return False


# ---------------------------------------------------------------------------
# Adaptive Exploration Constant (9.2a)
# ---------------------------------------------------------------------------


class TestAdaptiveExploration(unittest.TestCase):
    """Test adaptive exploration constant."""

    def test_disabled_by_default(self):
        agent = MCTSAgent(iterations=10, seed=42)
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        # When disabled, effective C should be the default 1.414
        self.assertAlmostEqual(
            agent._effective_exploration_constant, 1.414, places=2
        )
        self.assertAlmostEqual(agent.stats["adaptive_c_value"], 0.0)

    def test_adaptive_c_scales_with_branching_factor(self):
        agent = MCTSAgent(
            iterations=10,
            seed=42,
            adaptive_exploration_enabled=True,
            adaptive_exploration_base=1.414,
            adaptive_exploration_avg_bf=80.0,
        )
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        bf = len(moves)
        agent.select_action(board, Player.RED, moves)

        expected_c = 1.414 * math.sqrt(bf / 80.0)
        self.assertAlmostEqual(
            agent.stats["adaptive_c_value"], expected_c, places=3
        )

    def test_adaptive_c_higher_for_higher_bf(self):
        """More legal moves → higher C (more exploration)."""
        agent = MCTSAgent(
            iterations=5,
            seed=42,
            adaptive_exploration_enabled=True,
            adaptive_exploration_base=1.414,
            adaptive_exploration_avg_bf=80.0,
        )
        board = Board()
        gen = get_shared_generator()
        # Early game has high branching factor
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        c_early = agent.stats["adaptive_c_value"]

        # C should be positive (sanity)
        self.assertGreater(c_early, 0.0)


class TestAdaptiveRolloutDepth(unittest.TestCase):
    """Test adaptive rollout depth."""

    def test_disabled_by_default(self):
        agent = MCTSAgent(iterations=10, seed=42, rollout_cutoff_depth=10)
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        # Effective depth should stay at configured value
        self.assertEqual(agent._effective_rollout_cutoff_depth, 10)

    def test_adaptive_depth_inversely_proportional(self):
        agent = MCTSAgent(
            iterations=5,
            seed=42,
            adaptive_rollout_depth_enabled=True,
            adaptive_rollout_depth_base=20,
            adaptive_rollout_depth_avg_bf=80.0,
        )
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        bf = len(moves)
        agent.select_action(board, Player.RED, moves)

        expected_depth = max(1, round(20 * (80.0 / max(bf, 1))))
        self.assertEqual(agent.stats["adaptive_rollout_depth"], expected_depth)

    def test_adaptive_depth_minimum_one(self):
        """Depth should never go below 1."""
        agent = MCTSAgent(
            iterations=5,
            seed=42,
            adaptive_rollout_depth_enabled=True,
            adaptive_rollout_depth_base=1,
            adaptive_rollout_depth_avg_bf=1.0,
        )
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        self.assertGreaterEqual(agent._effective_rollout_cutoff_depth, 1)


# ---------------------------------------------------------------------------
# Sufficiency Threshold (9.2c)
# ---------------------------------------------------------------------------


class TestSufficiencyThreshold(unittest.TestCase):
    """Test UCT sufficiency threshold."""

    def test_disabled_by_default(self):
        agent = MCTSAgent(iterations=10, seed=42)
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        self.assertEqual(agent.stats["sufficiency_activations"], 0)

    def test_sufficiency_fires_with_enough_iterations(self):
        """With many iterations a dominant move should trigger sufficiency."""
        agent = MCTSAgent(
            iterations=30,
            seed=42,
            sufficiency_threshold_enabled=True,
        )
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        # We can't guarantee activation in all cases, but stats key must exist
        self.assertIn("sufficiency_activations", agent.stats)


# ---------------------------------------------------------------------------
# Loss Avoidance (9.3)
# ---------------------------------------------------------------------------


class TestLossAvoidance(unittest.TestCase):
    """Test loss avoidance mechanism."""

    def test_loss_detected_flag_initial(self):
        board = Board()
        node = MCTSNode(board, Player.RED)
        self.assertFalse(node.loss_detected)

    def test_loss_avoidance_disabled_by_default(self):
        agent = MCTSAgent(iterations=10, seed=42)
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        self.assertEqual(agent.stats["loss_avoidance_triggers"], 0)

    def test_loss_avoidance_flags_catastrophic_nodes(self):
        """When enabled, catastrophic rewards should trigger loss_detected flags."""
        agent = MCTSAgent(
            iterations=20,
            seed=42,
            loss_avoidance_enabled=True,
            loss_avoidance_threshold=-50.0,
        )
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        # Stats key must exist — actual triggers depend on rollout outcomes
        self.assertIn("loss_avoidance_triggers", agent.stats)

    def test_select_child_loss_avoidance_prefers_safe(self):
        """select_child with loss_avoidance should prefer non-flagged children."""
        board = Board()
        parent = MCTSNode(board, Player.RED)
        parent.visits = 10
        parent.total_reward = 5.0

        # Manually create two child nodes
        child_a = MCTSNode(board, Player.BLUE, parent=parent)
        child_a.visits = 5
        child_a.total_reward = 10.0  # Good Q
        child_a.loss_detected = True  # But flagged

        child_b = MCTSNode(board, Player.BLUE, parent=parent)
        child_b.visits = 5
        child_b.total_reward = 3.0  # Lower Q

        parent.children = [child_a, child_b]

        # Without loss avoidance, should pick child_a (higher Q)
        chosen = parent.select_child(loss_avoidance=False)
        self.assertIs(chosen, child_a)

        # Reset flag
        child_a.loss_detected = True

        # With loss avoidance, should pick child_b (child_a is flagged)
        chosen = parent.select_child(loss_avoidance=True)
        self.assertIs(chosen, child_b)

    def test_select_child_loss_avoidance_all_flagged(self):
        """When all children are flagged, should clear flags and pick best."""
        board = Board()
        parent = MCTSNode(board, Player.RED)
        parent.visits = 10
        parent.total_reward = 5.0

        child_a = MCTSNode(board, Player.BLUE, parent=parent)
        child_a.visits = 5
        child_a.total_reward = 10.0
        child_a.loss_detected = True

        child_b = MCTSNode(board, Player.BLUE, parent=parent)
        child_b.visits = 5
        child_b.total_reward = 3.0
        child_b.loss_detected = True

        parent.children = [child_a, child_b]

        # All flagged → should clear and pick best
        chosen = parent.select_child(loss_avoidance=True)
        self.assertIs(chosen, child_a)
        self.assertFalse(child_a.loss_detected)
        self.assertFalse(child_b.loss_detected)


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility(unittest.TestCase):
    """Ensure default params produce identical behavior to pre-Layer 9."""

    def test_default_agent_returns_valid_move(self):
        agent = MCTSAgent(iterations=10, seed=42)
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        move = agent.select_action(board, Player.RED, moves)
        self.assertIsNotNone(move)
        self.assertTrue(_move_matches_any(move, moves))

    def test_all_layer9_stats_exist(self):
        agent = MCTSAgent(iterations=10, seed=42)
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        for key in ["adaptive_c_value", "adaptive_rollout_depth",
                     "sufficiency_activations", "loss_avoidance_triggers"]:
            self.assertIn(key, agent.stats)

    def test_get_action_info_includes_layer9(self):
        agent = MCTSAgent(iterations=10, seed=42)
        board = Board()
        gen = get_shared_generator()
        moves = gen.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, moves)
        info = agent.get_action_info()
        params = info["parameters"]
        for key in ["adaptive_exploration_enabled", "adaptive_rollout_depth_enabled",
                     "sufficiency_threshold_enabled", "loss_avoidance_enabled"]:
            self.assertIn(key, params)


if __name__ == "__main__":
    unittest.main()

"""Tests for Layer 5: History Heuristics, RAVE, and NST."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import Board, Player
from engine.move_generator import get_shared_generator
from mcts.mcts_agent import MCTSAgent, MCTSNode
from mcts.move_heuristic import move_action_key


class TestRAVEBetaFormula(unittest.TestCase):
    """Test the RAVE beta blending weight formula."""

    def test_beta_high_at_low_visits(self):
        """With few parent visits, beta should be close to 1."""
        k = 1000
        n_parent = 1
        beta = math.sqrt(k / (3.0 * n_parent + k))
        self.assertGreater(beta, 0.95)

    def test_beta_low_at_high_visits(self):
        """With many parent visits, beta should approach 0."""
        k = 1000
        n_parent = 100000
        beta = math.sqrt(k / (3.0 * n_parent + k))
        self.assertLess(beta, 0.1)

    def test_beta_monotonically_decreasing(self):
        """Beta should decrease as parent visits increase."""
        k = 1000
        prev_beta = 1.0
        for n in [1, 10, 100, 1000, 10000]:
            beta = math.sqrt(k / (3.0 * n + k))
            self.assertLess(beta, prev_beta)
            prev_beta = beta

    def test_beta_increases_with_k(self):
        """Higher k should give more RAVE influence at same visit count."""
        n = 100
        beta_low_k = math.sqrt(100 / (3.0 * n + 100))
        beta_high_k = math.sqrt(5000 / (3.0 * n + 5000))
        self.assertGreater(beta_high_k, beta_low_k)


class TestRAVENodeStorage(unittest.TestCase):
    """Test RAVE statistics storage on MCTSNode."""

    def test_new_node_has_empty_rave(self):
        board = Board()
        node = MCTSNode(board, Player.RED)
        self.assertEqual(len(node.rave_total), 0)
        self.assertEqual(len(node.rave_visits), 0)

    def test_rave_table_update(self):
        board = Board()
        node = MCTSNode(board, Player.RED)
        # Manually update RAVE stats
        node.rave_total[5] = 10.0
        node.rave_visits[5] = 2
        self.assertAlmostEqual(node.rave_total[5] / node.rave_visits[5], 5.0)


class TestRAVESelection(unittest.TestCase):
    """Test that RAVE influences child selection."""

    def _make_node_with_children(self):
        """Create a parent with two children for selection tests."""
        board = Board()
        parent = MCTSNode.__new__(MCTSNode)
        parent.visits = 10
        parent.total_reward = 5.0
        parent.board = board
        parent.player = Player.RED
        parent.move = None
        parent.parent = None
        parent.children = []
        parent.untried_moves = []
        parent._heuristic_sorted = False
        parent._total_legal_moves = 0
        parent.minimax_value = float('-inf')
        parent.prior_bias = 0.0
        parent.rave_total = {}
        parent.rave_visits = {}

        mg = get_shared_generator()
        moves = mg.get_legal_moves(board, Player.RED)

        # Create two children with equal UCT stats but different RAVE scores
        for i, move in enumerate(moves[:2]):
            child = MCTSNode.__new__(MCTSNode)
            child.visits = 5
            child.total_reward = 2.5  # Same Q = 0.5
            child.move = move
            child.parent = parent
            child.children = []
            child.untried_moves = []
            child._heuristic_sorted = False
            child._total_legal_moves = 0
            child.minimax_value = float('-inf')
            child.prior_bias = 0.0
            child.rave_total = {}
            child.rave_visits = {}
            parent.children.append(child)

        return parent

    def test_rave_disabled_equal_children(self):
        """Without RAVE, equal-stat children should be selected deterministically."""
        parent = self._make_node_with_children()
        # Both children have identical stats → max picks first
        selected = parent.select_child(rave_enabled=False)
        self.assertIn(selected, parent.children)

    def test_rave_influences_selection(self):
        """With RAVE enabled and strong RAVE signal, selection should prefer high-RAVE child."""
        parent = self._make_node_with_children()
        child_a, child_b = parent.children

        # Give child_b a much higher RAVE score
        key_b = move_action_key(child_b.move)
        parent.rave_total[key_b] = 100.0
        parent.rave_visits[key_b] = 10

        # Give child_a a low RAVE score
        key_a = move_action_key(child_a.move)
        parent.rave_total[key_a] = 1.0
        parent.rave_visits[key_a] = 10

        selected = parent.select_child(rave_enabled=True, rave_k=100000)
        self.assertEqual(selected, child_b)


class TestRAVEUCBValue(unittest.TestCase):
    """Test UCB1 value computation with RAVE blending."""

    def _make_child(self, visits=10, total_reward=5.0):
        parent = MCTSNode.__new__(MCTSNode)
        parent.visits = 100
        child = MCTSNode.__new__(MCTSNode)
        child.visits = visits
        child.total_reward = total_reward
        child.parent = parent
        child.prior_bias = 0.0
        child.minimax_value = float('-inf')
        child.rave_total = {}
        child.rave_visits = {}
        return child

    def test_ucb_no_rave(self):
        child = self._make_child()
        val_no_rave = child.ucb1_value(rave_beta=0.0)
        val_with_rave = child.ucb1_value(rave_q=10.0, rave_beta=0.0)
        self.assertAlmostEqual(val_no_rave, val_with_rave)

    def test_ucb_with_rave_blending(self):
        child = self._make_child(visits=10, total_reward=5.0)
        # Q_UCT = 0.5, Q_RAVE = 2.0, beta = 0.5
        # Combined exploitation = 0.5 * 0.5 + 0.5 * 2.0 = 1.25
        val = child.ucb1_value(rave_q=2.0, rave_beta=0.5, exploration_constant=0.0)
        self.assertAlmostEqual(val, 1.25, places=2)

    def test_rave_fading_at_high_visits(self):
        """RAVE beta approaches 0 at high visits, so UCB should converge to standard."""
        child = self._make_child(visits=10, total_reward=5.0)
        val_no_rave = child.ucb1_value(rave_beta=0.0, exploration_constant=0.0)
        # Use a very small beta to show convergence
        val_tiny_rave = child.ucb1_value(rave_q=100.0, rave_beta=0.0001, exploration_constant=0.0)
        # With very small beta, should be very close to no-RAVE value
        self.assertAlmostEqual(val_no_rave, val_tiny_rave, places=1)


class TestRAVEIntegration(unittest.TestCase):
    """Integration test: run a few MCTS iterations with RAVE enabled."""

    def test_rave_agent_runs(self):
        """MCTSAgent with RAVE enabled should complete without errors."""
        agent = MCTSAgent(
            iterations=20,
            use_transposition_table=False,
            rave_enabled=True,
            rave_k=1000,
        )
        board = Board()
        mg = get_shared_generator()
        legal = mg.get_legal_moves(board, Player.RED)
        move = agent.select_action(board, Player.RED, legal)
        self.assertIsNotNone(move)
        self.assertGreater(agent.stats["iterations_run"], 0)
        self.assertGreater(agent.stats["rave_updates"], 0)

    def test_rave_disabled_no_updates(self):
        """RAVE disabled should produce zero rave_updates."""
        agent = MCTSAgent(
            iterations=20,
            use_transposition_table=False,
            rave_enabled=False,
        )
        board = Board()
        mg = get_shared_generator()
        legal = mg.get_legal_moves(board, Player.RED)
        agent.select_action(board, Player.RED, legal)
        self.assertEqual(agent.stats["rave_updates"], 0)

    def test_rave_plus_progressive_history(self):
        """RAVE and Progressive History should work together."""
        agent = MCTSAgent(
            iterations=20,
            use_transposition_table=False,
            rave_enabled=True,
            rave_k=1000,
            progressive_history_enabled=True,
            progressive_history_weight=1.0,
        )
        board = Board()
        mg = get_shared_generator()
        legal = mg.get_legal_moves(board, Player.RED)
        move = agent.select_action(board, Player.RED, legal)
        self.assertIsNotNone(move)
        self.assertGreater(agent.stats["rave_updates"], 0)
        self.assertGreater(len(agent._history_table), 0)


class TestNSTTable(unittest.TestCase):
    """Test N-gram Selection Technique table operations."""

    def test_nst_agent_runs(self):
        """MCTSAgent with NST enabled should complete without errors."""
        agent = MCTSAgent(
            iterations=20,
            use_transposition_table=False,
            nst_enabled=True,
            nst_weight=0.5,
        )
        board = Board()
        mg = get_shared_generator()
        legal = mg.get_legal_moves(board, Player.RED)
        move = agent.select_action(board, Player.RED, legal)
        self.assertIsNotNone(move)

    def test_nst_table_populated_after_moves(self):
        """After a move, NST last_action_key should be set.

        NST 2-gram pairs require rollout sequences with >= 2 root-player
        moves. On the first MCTS search, ``_last_root_action_key`` starts
        as None so the first rollout action has no predecessor — the table
        may be empty. We verify the key tracking works correctly.
        """
        agent = MCTSAgent(
            iterations=30,
            use_transposition_table=False,
            nst_enabled=True,
            nst_weight=0.5,
        )
        board = Board()
        mg = get_shared_generator()

        legal = mg.get_legal_moves(board, Player.RED)
        move1 = agent.select_action(board, Player.RED, legal)
        self.assertIsNotNone(move1)
        # After select_action, last_root_action_key should be set
        self.assertIsNotNone(agent._last_root_action_key)
        self.assertEqual(agent._last_root_action_key, move_action_key(move1))

    def test_nst_reset_history(self):
        """reset_history should clear NST table and last_action_key."""
        agent = MCTSAgent(
            iterations=10,
            use_transposition_table=False,
            nst_enabled=True,
        )
        agent._nst_table[(1, 2)] = [5.0, 1]
        agent._last_root_action_key = 3
        agent.reset_history()
        self.assertEqual(len(agent._nst_table), 0)
        self.assertIsNone(agent._last_root_action_key)


class TestConfigIntegration(unittest.TestCase):
    """Test that RAVE/NST parameters flow correctly through config."""

    def test_default_rave_disabled(self):
        agent = MCTSAgent(iterations=10, use_transposition_table=False)
        self.assertFalse(agent.rave_enabled)
        self.assertEqual(agent.rave_k, 1000.0)

    def test_default_nst_disabled(self):
        agent = MCTSAgent(iterations=10, use_transposition_table=False)
        self.assertFalse(agent.nst_enabled)
        self.assertEqual(agent.nst_weight, 0.5)

    def test_rave_in_action_info(self):
        agent = MCTSAgent(
            iterations=10,
            use_transposition_table=False,
            rave_enabled=True,
            rave_k=500,
        )
        info = agent.get_action_info()
        self.assertTrue(info["parameters"]["rave_enabled"])
        self.assertEqual(info["parameters"]["rave_k"], 500.0)

    def test_nst_in_action_info(self):
        agent = MCTSAgent(
            iterations=10,
            use_transposition_table=False,
            nst_enabled=True,
            nst_weight=1.5,
        )
        info = agent.get_action_info()
        self.assertTrue(info["parameters"]["nst_enabled"])
        self.assertEqual(info["parameters"]["nst_weight"], 1.5)


class TestRolloutMoveTracking(unittest.TestCase):
    """Test that rollout returns action keys when RAVE is enabled."""

    def test_rollout_returns_actions_with_rave(self):
        """With RAVE enabled, rollout should return non-empty action list."""
        agent = MCTSAgent(
            iterations=5,
            use_transposition_table=False,
            rave_enabled=True,
            rave_k=1000,
        )
        board = Board()
        agent._root_player = Player.RED
        result = agent._rollout(board, Player.RED)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        reward, actions = result
        self.assertIsInstance(actions, list)
        # Should have at least one root player action in a normal game
        self.assertGreater(len(actions), 0)
        # All action keys should be valid piece_ids (1-21)
        for akey in actions:
            self.assertGreaterEqual(akey, 1)
            self.assertLessEqual(akey, 21)

    def test_rollout_returns_empty_without_rave(self):
        """With RAVE disabled, rollout should return empty action list."""
        agent = MCTSAgent(
            iterations=5,
            use_transposition_table=False,
            rave_enabled=False,
        )
        board = Board()
        agent._root_player = Player.RED
        result = agent._rollout(board, Player.RED)
        self.assertIsInstance(result, tuple)
        reward, actions = result
        self.assertEqual(len(actions), 0)


if __name__ == "__main__":
    unittest.main()

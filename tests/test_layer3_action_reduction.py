"""Tests for Layer 3: Action Reduction — Progressive Widening & Progressive History."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import Board, Player
from engine.move_generator import get_shared_generator
from mcts.mcts_agent import MCTSAgent, MCTSNode
from mcts.move_heuristic import (
    compute_move_heuristic,
    compute_move_heuristic_normalised,
    move_action_key,
    rank_moves_by_heuristic,
)
from analytics.tournament.tuning import get_tuning_set


class TestProgressiveWideningMath(unittest.TestCase):
    """Test the progressive widening child limit formula."""

    def _make_node(self, visits: int, n_children: int, n_untried: int):
        """Create a minimal node for testing."""
        node = MCTSNode.__new__(MCTSNode)
        node.visits = visits
        node.children = [None] * n_children
        node.untried_moves = [None] * n_untried
        node._total_legal_moves = n_children + n_untried
        node._heuristic_sorted = False
        return node

    def test_max_children_formula(self):
        node = self._make_node(100, 0, 50)
        # C_pw=2.0, alpha=0.5 → 2.0 * 100^0.5 = 20
        self.assertEqual(node.max_children_for_visits(2.0, 0.5), 20)

    def test_max_children_zero_visits(self):
        node = self._make_node(0, 0, 50)
        self.assertEqual(node.max_children_for_visits(2.0, 0.5), 2)

    def test_max_children_one_visit(self):
        node = self._make_node(1, 0, 50)
        self.assertEqual(node.max_children_for_visits(2.0, 0.5), 2)

    def test_should_expand_true(self):
        node = self._make_node(1, 0, 50)
        # 0 children < max(2) → should expand
        self.assertTrue(node.should_expand_pw(2.0, 0.5))

    def test_should_expand_false(self):
        node = self._make_node(1, 3, 50)
        # 3 children >= max(2) → should NOT expand
        self.assertFalse(node.should_expand_pw(2.0, 0.5))

    def test_should_expand_no_untried(self):
        node = self._make_node(1, 1, 0)
        # No untried moves → can't expand
        self.assertFalse(node.should_expand_pw(2.0, 0.5))

    def test_high_alpha_allows_more(self):
        node = self._make_node(10, 0, 100)
        # alpha=0.75: 2.0 * 10^0.75 ≈ 11.2 → 11
        mc = node.max_children_for_visits(2.0, 0.75)
        self.assertGreater(mc, 10)

    def test_low_alpha_restricts(self):
        node = self._make_node(10, 0, 100)
        # alpha=0.25: 2.0 * 10^0.25 ≈ 3.5 → 3
        mc = node.max_children_for_visits(2.0, 0.25)
        self.assertLessEqual(mc, 4)


class TestMoveHeuristic(unittest.TestCase):
    """Test the domain-specific move heuristic scoring."""

    def setUp(self):
        self.board = Board()
        self.mg = get_shared_generator()
        self.legal = self.mg.get_legal_moves(self.board, Player.RED)

    def test_heuristic_returns_float(self):
        if not self.legal:
            self.skipTest("No legal moves")
        score = compute_move_heuristic(self.board, Player.RED, self.legal[0], self.mg)
        self.assertIsInstance(score, float)

    def test_normalised_in_range(self):
        for move in self.legal[:10]:
            score = compute_move_heuristic_normalised(self.board, Player.RED, move, self.mg)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_larger_pieces_score_higher(self):
        """Piece size should be a significant component."""
        from engine.pieces import PieceGenerator
        pg = PieceGenerator()
        sizes = {p.id: p.size for p in pg.get_all_pieces()}

        # Find a size-5 and size-1 move
        large = [m for m in self.legal if sizes.get(m.piece_id, 0) == 5]
        small = [m for m in self.legal if sizes.get(m.piece_id, 0) == 1]
        if not large or not small:
            self.skipTest("Need both large and small pieces")
        large_score = compute_move_heuristic(self.board, Player.RED, large[0], self.mg)
        small_score = compute_move_heuristic(self.board, Player.RED, small[0], self.mg)
        self.assertGreater(large_score, small_score)

    def test_rank_moves_ascending(self):
        ranked = rank_moves_by_heuristic(self.board, Player.RED, self.legal, self.mg)
        scores = [s for s, m in ranked]
        self.assertEqual(scores, sorted(scores))

    def test_action_key_is_piece_id(self):
        if not self.legal:
            self.skipTest("No legal moves")
        key = move_action_key(self.legal[0])
        self.assertEqual(key, self.legal[0].piece_id)


class TestProgressiveHistoryIntegration(unittest.TestCase):
    """Test progressive history tracking in the agent."""

    def test_history_table_populated(self):
        board = Board()
        mg = get_shared_generator()
        legal = mg.get_legal_moves(board, Player.RED)
        if not legal:
            self.skipTest("No legal moves")

        agent = MCTSAgent(
            iterations=20,
            seed=42,
            progressive_history_enabled=True,
            progressive_history_weight=1.0,
        )
        agent.select_action(board, Player.RED, legal)
        self.assertGreater(len(agent._history_table), 0)
        self.assertGreater(agent.stats["history_table_size"], 0)

    def test_history_table_persists_across_moves(self):
        """History table should NOT be cleared by reset()."""
        agent = MCTSAgent(
            iterations=5,
            seed=42,
            progressive_history_enabled=True,
            progressive_history_weight=1.0,
        )
        board = Board()
        mg = get_shared_generator()
        legal = mg.get_legal_moves(board, Player.RED)
        if not legal:
            self.skipTest("No legal moves")

        agent.select_action(board, Player.RED, legal)
        size_before = len(agent._history_table)
        agent.reset()
        self.assertEqual(len(agent._history_table), size_before)

    def test_reset_history_clears_table(self):
        agent = MCTSAgent(
            iterations=5,
            seed=42,
            progressive_history_enabled=True,
            progressive_history_weight=1.0,
        )
        board = Board()
        mg = get_shared_generator()
        legal = mg.get_legal_moves(board, Player.RED)
        if not legal:
            self.skipTest("No legal moves")

        agent.select_action(board, Player.RED, legal)
        self.assertGreater(len(agent._history_table), 0)
        agent.reset_history()
        self.assertEqual(len(agent._history_table), 0)


class TestProgressiveWideningAgent(unittest.TestCase):
    """Integration tests for progressive widening in the agent."""

    def test_pw_agent_returns_valid_move(self):
        board = Board()
        mg = get_shared_generator()
        legal = mg.get_legal_moves(board, Player.RED)
        if not legal:
            self.skipTest("No legal moves")

        agent = MCTSAgent(
            iterations=20,
            seed=42,
            progressive_widening_enabled=True,
            pw_c=2.0,
            pw_alpha=0.5,
            heuristic_move_ordering=True,
        )
        move = agent.select_action(board, Player.RED, legal)
        self.assertIsNotNone(move)
        # Verify the selected move is legal
        legal_tuples = {(m.piece_id, m.orientation, m.anchor_row, m.anchor_col) for m in legal}
        self.assertIn(
            (move.piece_id, move.orientation, move.anchor_row, move.anchor_col),
            legal_tuples,
        )

    def test_combined_pw_ph_agent(self):
        board = Board()
        mg = get_shared_generator()
        legal = mg.get_legal_moves(board, Player.RED)
        if not legal:
            self.skipTest("No legal moves")

        agent = MCTSAgent(
            iterations=20,
            seed=42,
            progressive_widening_enabled=True,
            pw_c=2.0,
            pw_alpha=0.5,
            progressive_history_enabled=True,
            progressive_history_weight=1.0,
            heuristic_move_ordering=True,
        )
        move = agent.select_action(board, Player.RED, legal)
        self.assertIsNotNone(move)

    def test_get_action_info_includes_layer3_params(self):
        agent = MCTSAgent(
            iterations=5,
            seed=42,
            progressive_widening_enabled=True,
            pw_c=3.0,
            pw_alpha=0.4,
            progressive_history_enabled=True,
            progressive_history_weight=2.0,
            heuristic_move_ordering=True,
        )
        info = agent.get_action_info()
        params = info["parameters"]
        self.assertTrue(params["progressive_widening_enabled"])
        self.assertAlmostEqual(params["pw_c"], 3.0)
        self.assertAlmostEqual(params["pw_alpha"], 0.4)
        self.assertTrue(params["progressive_history_enabled"])
        self.assertAlmostEqual(params["progressive_history_weight"], 2.0)
        self.assertTrue(params["heuristic_move_ordering"])


class TestTuningSets(unittest.TestCase):
    """Test that Layer 3 tuning sets are registered correctly."""

    def test_pw_sweep_exists(self):
        ts = get_tuning_set("pw_sweep")
        self.assertEqual(len(ts.tunings), 4)

    def test_ph_sweep_exists(self):
        ts = get_tuning_set("ph_sweep")
        self.assertEqual(len(ts.tunings), 4)

    def test_action_reduction_ablation_exists(self):
        ts = get_tuning_set("action_reduction_ablation")
        self.assertEqual(len(ts.tunings), 4)
        names = {t.name for t in ts.tunings}
        self.assertIn("baseline", names)
        self.assertIn("pw_only", names)
        self.assertIn("pw_plus_ph", names)

    def test_pw_params_resolve(self):
        ts = get_tuning_set("pw_sweep")
        for tuning in ts.tunings:
            params = tuning.resolve_params(200)
            self.assertIsInstance(params, dict)


if __name__ == "__main__":
    unittest.main()

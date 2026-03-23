"""Tests for Layer 8: Parallelization of MCTS."""

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
# MCTSNode virtual loss tests
# ---------------------------------------------------------------------------


class TestVirtualLoss(unittest.TestCase):
    """Test virtual loss application and removal on MCTSNode."""

    def test_virtual_loss_initial_zero(self):
        board = Board()
        node = MCTSNode(board, Player.RED)
        self.assertEqual(node.virtual_losses, 0)

    def test_apply_virtual_loss(self):
        board = Board()
        node = MCTSNode(board, Player.RED)
        initial_visits = node.visits
        initial_reward = node.total_reward

        node.apply_virtual_loss(1.0)

        self.assertEqual(node.virtual_losses, 1)
        self.assertEqual(node.visits, initial_visits + 1)
        self.assertAlmostEqual(node.total_reward, initial_reward - 1.0)

    def test_remove_virtual_loss(self):
        board = Board()
        node = MCTSNode(board, Player.RED)
        node.apply_virtual_loss(1.0)
        node.remove_virtual_loss(1.0)

        self.assertEqual(node.virtual_losses, 0)
        self.assertEqual(node.visits, 0)
        self.assertAlmostEqual(node.total_reward, 0.0)

    def test_multiple_virtual_losses(self):
        board = Board()
        node = MCTSNode(board, Player.RED)

        node.apply_virtual_loss(1.0)
        node.apply_virtual_loss(1.0)
        node.apply_virtual_loss(1.0)

        self.assertEqual(node.virtual_losses, 3)
        self.assertEqual(node.visits, 3)
        self.assertAlmostEqual(node.total_reward, -3.0)

        node.remove_virtual_loss(1.0)
        node.remove_virtual_loss(1.0)
        node.remove_virtual_loss(1.0)

        self.assertEqual(node.virtual_losses, 0)
        self.assertEqual(node.visits, 0)
        self.assertAlmostEqual(node.total_reward, 0.0)

    def test_virtual_loss_reduces_ucb(self):
        """Virtual loss should make a node less attractive in UCB selection."""
        board = Board()
        parent = MCTSNode(board, Player.RED)
        parent.visits = 100

        child = MCTSNode(board, Player.BLUE, parent=parent)
        child.visits = 10
        child.total_reward = 5.0
        parent.children.append(child)

        ucb_before = child.ucb1_value()

        child.apply_virtual_loss(1.0)
        ucb_after = child.ucb1_value()

        self.assertLess(ucb_after, ucb_before)


# ---------------------------------------------------------------------------
# MCTSAgent parallelization parameter tests
# ---------------------------------------------------------------------------


class TestParallelizationParams(unittest.TestCase):
    """Test Layer 8 parameter validation and defaults."""

    def test_default_single_worker(self):
        agent = MCTSAgent(iterations=10)
        self.assertEqual(agent.num_workers, 1)
        self.assertAlmostEqual(agent.virtual_loss, 1.0)
        self.assertEqual(agent.parallel_strategy, "root")

    def test_custom_params(self):
        agent = MCTSAgent(
            iterations=10,
            num_workers=4,
            virtual_loss=2.0,
            parallel_strategy="tree",
        )
        self.assertEqual(agent.num_workers, 4)
        self.assertAlmostEqual(agent.virtual_loss, 2.0)
        self.assertEqual(agent.parallel_strategy, "tree")

    def test_invalid_strategy_raises(self):
        with self.assertRaises(ValueError):
            MCTSAgent(iterations=10, parallel_strategy="invalid")

    def test_num_workers_clamped_to_1(self):
        agent = MCTSAgent(iterations=10, num_workers=0)
        self.assertEqual(agent.num_workers, 1)

    def test_stats_include_parallel_keys(self):
        agent = MCTSAgent(iterations=10)
        self.assertIn("parallel_workers", agent.stats)
        self.assertIn("parallel_strategy", agent.stats)
        self.assertIn("parallel_trees_merged", agent.stats)
        self.assertIn("virtual_loss_applications", agent.stats)

    def test_get_action_info_includes_layer8(self):
        agent = MCTSAgent(iterations=10, num_workers=2)
        info = agent.get_action_info()
        params = info["parameters"]
        self.assertEqual(params["num_workers"], 2)
        self.assertAlmostEqual(params["virtual_loss"], 1.0)
        self.assertEqual(params["parallel_strategy"], "root")

    def test_reset_clears_parallel_stats(self):
        agent = MCTSAgent(iterations=10)
        agent.stats["parallel_workers"] = 4
        agent.stats["parallel_trees_merged"] = 3
        agent.reset()
        self.assertEqual(agent.stats["parallel_workers"], 0)
        self.assertEqual(agent.stats["parallel_trees_merged"], 0)


# ---------------------------------------------------------------------------
# Single-worker (no regression) tests
# ---------------------------------------------------------------------------


class TestSingleWorkerUnchanged(unittest.TestCase):
    """Verify that num_workers=1 produces identical behavior to baseline."""

    def test_single_worker_returns_valid_move(self):
        board = Board()
        agent = MCTSAgent(iterations=50, seed=42, num_workers=1)
        move_gen = get_shared_generator()
        legal_moves = move_gen.get_legal_moves(board, Player.RED)

        move = agent.select_action(board, Player.RED, legal_moves)
        self.assertIsNotNone(move)
        self.assertTrue(
            _move_matches_any(move, legal_moves),
            "Returned move should match a legal move by attributes",
        )

    def test_single_worker_stats_no_parallel(self):
        """Single worker should not set parallel stats."""
        board = Board()
        agent = MCTSAgent(iterations=50, seed=42, num_workers=1)
        move_gen = get_shared_generator()
        legal_moves = move_gen.get_legal_moves(board, Player.RED)

        agent.select_action(board, Player.RED, legal_moves)
        self.assertEqual(agent.stats["parallel_workers"], 0)
        self.assertEqual(agent.stats["parallel_strategy"], "none")


# ---------------------------------------------------------------------------
# Tree parallelization tests
# ---------------------------------------------------------------------------


class TestTreeParallelization(unittest.TestCase):
    """Test tree parallelization with virtual loss (threading)."""

    def test_tree_parallel_returns_valid_move(self):
        board = Board()
        agent = MCTSAgent(
            iterations=100,
            seed=42,
            num_workers=2,
            parallel_strategy="tree",
        )
        move_gen = get_shared_generator()
        legal_moves = move_gen.get_legal_moves(board, Player.RED)

        move = agent.select_action(board, Player.RED, legal_moves)
        self.assertIsNotNone(move)
        self.assertTrue(
            _move_matches_any(move, legal_moves),
            "Tree-parallel move should match a legal move by attributes",
        )

    def test_tree_parallel_sets_stats(self):
        board = Board()
        agent = MCTSAgent(
            iterations=100,
            seed=42,
            num_workers=2,
            parallel_strategy="tree",
        )
        move_gen = get_shared_generator()
        legal_moves = move_gen.get_legal_moves(board, Player.RED)

        agent.select_action(board, Player.RED, legal_moves)
        self.assertEqual(agent.stats["parallel_workers"], 2)
        self.assertEqual(agent.stats["parallel_strategy"], "tree")
        self.assertGreater(agent.stats["iterations_run"], 0)
        self.assertGreater(agent.stats["virtual_loss_applications"], 0)

    def test_tree_parallel_virtual_losses_cleaned_up(self):
        """After search completes, all virtual losses should be removed."""
        board = Board()
        agent = MCTSAgent(
            iterations=50,
            seed=42,
            num_workers=2,
            parallel_strategy="tree",
        )
        move_gen = get_shared_generator()
        legal_moves = move_gen.get_legal_moves(board, Player.RED)

        # Run tree-parallel MCTS
        agent._root_player = Player.RED
        root = MCTSNode(board, Player.RED)
        agent._run_mcts_tree_parallel(root)

        # Check that no nodes have leftover virtual losses
        stack = [root]
        while stack:
            node = stack.pop()
            self.assertEqual(
                node.virtual_losses, 0,
                f"Node at depth has {node.virtual_losses} leftover virtual losses"
            )
            stack.extend(node.children)


# ---------------------------------------------------------------------------
# Root parallelization tests
# ---------------------------------------------------------------------------


class TestRootParallelization(unittest.TestCase):
    """Test root parallelization (multiprocessing)."""

    def test_root_parallel_returns_valid_move(self):
        board = Board()
        agent = MCTSAgent(
            iterations=100,
            seed=42,
            num_workers=2,
            parallel_strategy="root",
        )
        move_gen = get_shared_generator()
        legal_moves = move_gen.get_legal_moves(board, Player.RED)

        move = agent.select_action(board, Player.RED, legal_moves)
        self.assertIsNotNone(move)
        self.assertTrue(
            _move_matches_any(move, legal_moves),
            "Root-parallel move should match a legal move by attributes",
        )

    def test_root_parallel_sets_stats(self):
        board = Board()
        agent = MCTSAgent(
            iterations=100,
            seed=42,
            num_workers=2,
            parallel_strategy="root",
        )
        move_gen = get_shared_generator()
        legal_moves = move_gen.get_legal_moves(board, Player.RED)

        agent.select_action(board, Player.RED, legal_moves)
        self.assertEqual(agent.stats["parallel_workers"], 2)
        self.assertEqual(agent.stats["parallel_strategy"], "root")
        self.assertGreater(agent.stats["parallel_trees_merged"], 0)

    def test_root_parallel_single_legal_move(self):
        """With only one legal move, should return it immediately."""
        board = Board()
        agent = MCTSAgent(
            iterations=100,
            seed=42,
            num_workers=2,
            parallel_strategy="root",
        )
        move_gen = get_shared_generator()
        legal_moves = move_gen.get_legal_moves(board, Player.RED)

        # Pass just one legal move
        move = agent.select_action(board, Player.RED, [legal_moves[0]])
        self.assertEqual(move, legal_moves[0])

    def test_root_parallel_no_legal_moves(self):
        board = Board()
        agent = MCTSAgent(
            iterations=100,
            seed=42,
            num_workers=2,
            parallel_strategy="root",
        )
        move = agent.select_action(board, Player.RED, [])
        self.assertIsNone(move)


# ---------------------------------------------------------------------------
# Parallel module unit tests
# ---------------------------------------------------------------------------


class TestParallelModule(unittest.TestCase):
    """Test functions in mcts.parallel module."""

    def test_move_key_consistency(self):
        from mcts.parallel import _move_key
        move_gen = get_shared_generator()
        board = Board()
        legal_moves = move_gen.get_legal_moves(board, Player.RED)

        if legal_moves:
            move = legal_moves[0]
            key1 = _move_key(move)
            key2 = _move_key(move)
            self.assertEqual(key1, key2)

    def test_extract_agent_config(self):
        from mcts.parallel import _extract_agent_config
        agent = MCTSAgent(
            iterations=500,
            exploration_constant=2.0,
            num_workers=4,
            rave_enabled=True,
        )
        config = _extract_agent_config(agent)

        self.assertEqual(config["iterations"], 500)
        self.assertAlmostEqual(config["exploration_constant"], 2.0)
        self.assertEqual(config["num_workers"], 1)  # forced single-threaded in workers
        self.assertTrue(config["rave_enabled"])

    def test_extract_config_forces_single_worker(self):
        """Worker config must have num_workers=1 to prevent recursive parallelism."""
        from mcts.parallel import _extract_agent_config
        agent = MCTSAgent(iterations=100, num_workers=8)
        config = _extract_agent_config(agent)
        self.assertEqual(config["num_workers"], 1)


# ---------------------------------------------------------------------------
# Config passthrough tests
# ---------------------------------------------------------------------------


class TestConfigPassthrough(unittest.TestCase):
    """Test that arena config Layer 8 params reach the agent."""

    def test_arena_runner_passes_layer8_params(self):
        """Verify build_agent passes through num_workers and parallel_strategy."""
        from analytics.tournament.arena_runner import AgentConfig, build_agent

        config = AgentConfig(
            name="test_parallel",
            type="mcts",
            thinking_time_ms=10,
            params={
                "deterministic_time_budget": True,
                "iterations_per_ms": 10.0,
                "num_workers": 4,
                "virtual_loss": 2.0,
                "parallel_strategy": "tree",
            },
        )
        adapter = build_agent(config, seed=42)
        # The adapter wraps the MCTSAgent — access through the adapter
        inner_agent = adapter.agent
        self.assertEqual(inner_agent.num_workers, 4)
        self.assertAlmostEqual(inner_agent.virtual_loss, 2.0)
        self.assertEqual(inner_agent.parallel_strategy, "tree")


if __name__ == "__main__":
    unittest.main()

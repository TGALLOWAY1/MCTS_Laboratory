"""Tests for Layer 7: Opponent Modeling in 4-Player Blokus."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import Board, Player
from engine.move_generator import LegalMoveGenerator, get_shared_generator
from mcts.opponent_model import (
    BlockingTracker,
    KingMakerDetector,
    OpponentModelManager,
    OpponentProfile,
)
from mcts.mcts_agent import MCTSAgent


# ---------------------------------------------------------------------------
# BlockingTracker tests
# ---------------------------------------------------------------------------


class TestBlockingTracker(unittest.TestCase):
    """Test blocking rate tracking and targeting detection."""

    def test_empty_tracker(self):
        tracker = BlockingTracker()
        self.assertAlmostEqual(
            tracker.get_blocking_rate(Player.RED, Player.BLUE), 0.0
        )
        self.assertFalse(tracker.is_targeting(Player.RED, Player.BLUE))

    def test_record_move_no_blocking(self):
        """A move that doesn't block anyone should record zero blocking."""
        board = Board()
        tracker = BlockingTracker()
        # Simulate a move that doesn't change opponent frontiers
        # (board_before == board_after means no blocking)
        blocked = tracker.record_move(board, board, Player.RED)
        self.assertEqual(tracker.move_counts[Player.RED.value], 1)
        # No blocking because frontiers are identical
        self.assertEqual(len(blocked), 0)

    def test_blocking_rate_increases_with_blocks(self):
        """Manually constructed blocking scenario."""
        tracker = BlockingTracker()
        # Simulate blocking by using two different board states
        board_before = Board()
        board_after = Board()

        # Place a RED piece near BLUE's start corner to create blocking
        # BLUE starts at (0, 19) — their frontier starts as {(0, 19)}
        # If RED places near there, BLUE's frontier could shrink

        # We'll use a simulated approach: make multiple boards
        # and record moves manually
        # For now, test the math with direct manipulation
        tracker.move_counts[Player.RED.value] = 5
        tracker.blocking_counts[(Player.RED.value, Player.BLUE.value)] = 10
        tracker.blocking_counts[(Player.RED.value, Player.YELLOW.value)] = 2
        tracker.blocking_counts[(Player.RED.value, Player.GREEN.value)] = 3

        # RED blocks BLUE at rate 10/5 = 2.0
        self.assertAlmostEqual(
            tracker.get_blocking_rate(Player.RED, Player.BLUE), 2.0
        )
        # Average blocking rate = (2.0 + 0.4 + 0.6) / 3 = 1.0
        self.assertAlmostEqual(
            tracker.get_avg_blocking_rate(Player.RED), 1.0
        )

    def test_targeting_detection(self):
        """Player targeting when blocking rate > 2x average."""
        tracker = BlockingTracker()
        tracker.move_counts[Player.RED.value] = 10
        tracker.blocking_counts[(Player.RED.value, Player.BLUE.value)] = 30
        tracker.blocking_counts[(Player.RED.value, Player.YELLOW.value)] = 5
        tracker.blocking_counts[(Player.RED.value, Player.GREEN.value)] = 5

        # RED vs BLUE: 30/10 = 3.0
        # Average: (3.0 + 0.5 + 0.5) / 3 = 1.333
        # 3.0 > 2.0 * 1.333 = 2.667 → targeting
        self.assertTrue(
            tracker.is_targeting(Player.RED, Player.BLUE, threshold=2.0)
        )
        # YELLOW is not targeted
        self.assertFalse(
            tracker.is_targeting(Player.RED, Player.YELLOW, threshold=2.0)
        )

    def test_targeting_requires_minimum_moves(self):
        """Don't flag targeting with fewer than 3 moves."""
        tracker = BlockingTracker()
        tracker.move_counts[Player.RED.value] = 2
        tracker.blocking_counts[(Player.RED.value, Player.BLUE.value)] = 20
        self.assertFalse(
            tracker.is_targeting(Player.RED, Player.BLUE, threshold=2.0)
        )

    def test_reset_clears_state(self):
        tracker = BlockingTracker()
        tracker.move_counts[Player.RED.value] = 5
        tracker.blocking_counts[(1, 2)] = 10
        tracker.reset()
        self.assertEqual(len(tracker.move_counts), 0)
        self.assertEqual(len(tracker.blocking_counts), 0)


# ---------------------------------------------------------------------------
# KingMakerDetector tests
# ---------------------------------------------------------------------------


class TestKingMakerDetector(unittest.TestCase):
    """Test late-game king-maker detection."""

    def test_early_game_all_contenders(self):
        """Before late threshold, everyone is a contender."""
        detector = KingMakerDetector(score_gap_threshold=15, occupancy_threshold=0.55)
        board = Board()
        roles = detector.detect(board)
        for p in [Player.RED, Player.BLUE, Player.YELLOW, Player.GREEN]:
            self.assertEqual(roles[p], "contender")

    def test_get_leader(self):
        """Leader is the player with highest score."""
        detector = KingMakerDetector()
        board = Board()
        # On empty board all scores are 0, so any player can be "leader"
        leader = detector.get_leader(board)
        self.assertIn(leader, [Player.RED, Player.BLUE, Player.YELLOW, Player.GREEN])

    def test_occupancy_computation(self):
        """Board occupancy should be 0 on empty board."""
        detector = KingMakerDetector()
        board = Board()
        self.assertAlmostEqual(detector.get_board_occupancy(board), 0.0)

    def test_kingmaker_target_is_leader(self):
        """King-maker's likely target should be the leader."""
        detector = KingMakerDetector()
        board = Board()
        # With all scores at 0, the leader is arbitrary but the function should work
        target = detector.get_likely_target(board, Player.GREEN)
        # Target is None only if GREEN is the leader
        if target is not None:
            self.assertNotEqual(target, Player.GREEN)


# ---------------------------------------------------------------------------
# OpponentProfile tests
# ---------------------------------------------------------------------------


class TestOpponentProfile(unittest.TestCase):
    """Test adaptive opponent profiling across games."""

    def test_initial_values(self):
        profile = OpponentProfile()
        self.assertAlmostEqual(profile.avg_piece_size_preference, 0.5)
        self.assertAlmostEqual(profile.blocking_tendency, 0.5)
        self.assertAlmostEqual(profile.center_preference, 0.5)
        self.assertEqual(profile.games_observed, 0)

    def test_first_game_sets_values(self):
        profile = OpponentProfile()
        profile.update_from_game(
            total_moves=10,
            avg_piece_size=0.8,
            blocking_rate=0.3,
            center_proximity=0.7,
        )
        self.assertAlmostEqual(profile.avg_piece_size_preference, 0.8)
        self.assertAlmostEqual(profile.blocking_tendency, 0.3)
        self.assertAlmostEqual(profile.center_preference, 0.7)
        self.assertEqual(profile.games_observed, 1)

    def test_ema_update(self):
        """Subsequent games use exponential moving average."""
        profile = OpponentProfile()
        profile.update_from_game(10, 0.8, 0.3, 0.7)
        profile.update_from_game(10, 0.4, 0.9, 0.3)

        # EMA with alpha=0.3: new = 0.3*current + 0.7*old
        expected_size = 0.3 * 0.4 + 0.7 * 0.8  # 0.68
        self.assertAlmostEqual(profile.avg_piece_size_preference, expected_size)
        self.assertEqual(profile.games_observed, 2)

    def test_zero_moves_no_update(self):
        profile = OpponentProfile()
        profile.update_from_game(0, 0.8, 0.3, 0.7)
        self.assertEqual(profile.games_observed, 0)

    def test_to_dict(self):
        profile = OpponentProfile()
        d = profile.to_dict()
        self.assertIn("avg_piece_size_preference", d)
        self.assertIn("games_observed", d)


# ---------------------------------------------------------------------------
# OpponentModelManager tests
# ---------------------------------------------------------------------------


class TestOpponentModelManager(unittest.TestCase):
    """Test the central opponent model coordinator."""

    def test_initialization(self):
        mgr = OpponentModelManager(
            root_player=Player.RED,
            alliance_detection_enabled=True,
            kingmaker_detection_enabled=True,
        )
        self.assertEqual(mgr.root_player, Player.RED)
        self.assertFalse(mgr.is_targeting_root(Player.BLUE))
        self.assertEqual(mgr.get_role(Player.BLUE), "contender")

    def test_get_opponent_rollout_policy_default(self):
        """Without any flags, returns the default policy."""
        mgr = OpponentModelManager(root_player=Player.RED)
        self.assertEqual(
            mgr.get_opponent_rollout_policy(Player.BLUE, "random"), "random"
        )

    def test_targeting_upgrades_policy(self):
        """When alliance detection flags a player, their policy upgrades to heuristic."""
        mgr = OpponentModelManager(
            root_player=Player.RED,
            alliance_detection_enabled=True,
        )
        # Manually set targeting flag
        mgr._targeting_players.add(Player.BLUE.value)
        policy = mgr.get_opponent_rollout_policy(Player.BLUE, "random")
        self.assertEqual(policy, "heuristic")

    def test_defensive_eval_adjustment_empty_when_no_threat(self):
        mgr = OpponentModelManager(root_player=Player.RED)
        board = Board()
        adjustments = mgr.get_defensive_eval_adjustment(board)
        self.assertEqual(len(adjustments), 0)

    def test_defensive_eval_adjustment_nonempty_when_targeted(self):
        mgr = OpponentModelManager(
            root_player=Player.RED,
            defensive_weight_shift=0.15,
        )
        mgr._targeting_players.add(Player.BLUE.value)
        board = Board()
        adjustments = mgr.get_defensive_eval_adjustment(board)
        self.assertIn("accessible_corners", adjustments)
        self.assertGreater(adjustments["accessible_corners"], 0)

    def test_reset_game_preserves_profiles(self):
        mgr = OpponentModelManager(
            root_player=Player.RED,
            adaptive_enabled=True,
        )
        # Create a profile
        profile = mgr.get_profile(Player.BLUE)
        profile.update_from_game(10, 0.8, 0.3, 0.7)

        # Simulate some blocking
        mgr.blocking_tracker.move_counts[Player.BLUE.value] = 5

        # Reset game
        mgr.reset_game()

        # Blocking tracker should be cleared
        self.assertEqual(len(mgr.blocking_tracker.move_counts), 0)
        # But profiles should persist
        self.assertEqual(mgr.get_profile(Player.BLUE).games_observed, 1)

    def test_get_stats(self):
        mgr = OpponentModelManager(root_player=Player.RED)
        stats = mgr.get_stats()
        self.assertIn("targeting_count", stats)
        self.assertEqual(stats["targeting_count"], 0)


# ---------------------------------------------------------------------------
# MCTSAgent Layer 7 integration tests
# ---------------------------------------------------------------------------


class TestMCTSAgentOpponentRollout(unittest.TestCase):
    """Test MCTSAgent with asymmetric rollout policies."""

    def test_default_backward_compatible(self):
        """Default params should not change behavior (opponent_rollout_policy='same')."""
        agent = MCTSAgent(iterations=10, seed=42)
        self.assertEqual(agent.opponent_rollout_policy, "same")
        self.assertFalse(agent.opponent_modeling_enabled)
        self.assertIsNone(agent._opponent_model)

    def test_self_focused_config(self):
        """Self-focused config: heuristic for self, random for opponents."""
        agent = MCTSAgent(
            iterations=10,
            seed=42,
            rollout_policy="heuristic",
            opponent_rollout_policy="random",
        )
        self.assertEqual(agent.rollout_policy, "heuristic")
        self.assertEqual(agent.opponent_rollout_policy, "random")

    def test_invalid_opponent_rollout_policy(self):
        """Invalid opponent_rollout_policy should raise ValueError."""
        with self.assertRaises(ValueError):
            MCTSAgent(iterations=10, opponent_rollout_policy="invalid")

    def test_opponent_modeling_creates_manager(self):
        """When opponent_modeling_enabled, select_action creates the manager."""
        agent = MCTSAgent(
            iterations=5,
            seed=42,
            opponent_modeling_enabled=True,
            alliance_detection_enabled=True,
        )
        board = Board()
        mg = get_shared_generator()
        legal_moves = mg.get_legal_moves(board, Player.RED)
        if legal_moves:
            agent.select_action(board, Player.RED, legal_moves)
            self.assertIsNotNone(agent._opponent_model)
            self.assertEqual(agent._opponent_model.root_player, Player.RED)

    def test_notify_move_no_crash(self):
        """notify_move should not crash even without opponent model."""
        agent = MCTSAgent(iterations=5, seed=42)
        board = Board()
        # Should be a no-op
        agent.notify_move(board, board, Player.RED)

    def test_notify_move_with_model(self):
        """notify_move should forward to opponent model when enabled."""
        agent = MCTSAgent(
            iterations=5,
            seed=42,
            opponent_modeling_enabled=True,
            alliance_detection_enabled=True,
        )
        board = Board()
        mg = get_shared_generator()
        legal_moves = mg.get_legal_moves(board, Player.RED)
        if legal_moves:
            # Trigger model creation
            agent.select_action(board, Player.RED, legal_moves)
            # Now notify — should update the blocking tracker
            agent.notify_move(board, board, Player.RED)
            self.assertEqual(
                agent._opponent_model.blocking_tracker.move_counts.get(Player.RED.value, 0),
                1,
            )

    def test_reset_opponent_model_game(self):
        agent = MCTSAgent(
            iterations=5,
            seed=42,
            opponent_modeling_enabled=True,
        )
        board = Board()
        mg = get_shared_generator()
        legal_moves = mg.get_legal_moves(board, Player.RED)
        if legal_moves:
            agent.select_action(board, Player.RED, legal_moves)
            agent.notify_move(board, board, Player.BLUE)
            agent.reset_opponent_model_game()
            self.assertEqual(
                len(agent._opponent_model.blocking_tracker.move_counts), 0
            )

    def test_get_opponent_model_stats(self):
        """Stats should be empty dict when model is not initialized."""
        agent = MCTSAgent(iterations=5, seed=42)
        self.assertEqual(agent.get_opponent_model_stats(), {})

    def test_asymmetric_rollout_runs_without_error(self):
        """Full MCTS run with asymmetric rollout should complete."""
        agent = MCTSAgent(
            iterations=20,
            seed=42,
            rollout_policy="heuristic",
            opponent_rollout_policy="random",
        )
        board = Board()
        mg = get_shared_generator()
        legal_moves = mg.get_legal_moves(board, Player.RED)
        if legal_moves:
            move = agent.select_action(board, Player.RED, legal_moves)
            self.assertIsNotNone(move)
            # Check that opponent rollout stats were recorded
            stats = agent.stats
            self.assertIn("opponent_random_rollouts", stats)


if __name__ == "__main__":
    unittest.main()

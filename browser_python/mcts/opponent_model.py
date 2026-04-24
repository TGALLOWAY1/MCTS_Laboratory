"""Layer 7: Opponent Modeling for 4-Player Blokus.

Provides blocking-rate tracking, alliance detection, king-maker awareness,
and adaptive opponent modeling for repeated play. Used by MCTSAgent to
implement asymmetric rollout policies and defensive evaluation shifts.

References:
- Baier & Kaisers (2020): Opponent Move Abstractions (OMA)
- ColosseumRL (2019): Emergent alliances in multi-player games
- Nijssen thesis, Statement #4: Self-importance in fixed coalitions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from engine.board import Board, Player

# All four players in turn order
_PLAYERS: List[Player] = [Player.RED, Player.BLUE, Player.YELLOW, Player.GREEN]


# ---------------------------------------------------------------------------
# 7.2 — Blocking Rate Tracker
# ---------------------------------------------------------------------------

class BlockingTracker:
    """Tracks per-opponent blocking rates during actual gameplay.

    After each move, records how many frontier cells were eliminated for
    each opponent. A blocking event occurs when a placed piece's orthogonal
    adjacency removes a frontier cell from another player's frontier set.
    """

    def __init__(self) -> None:
        # {(blocker_value, victim_value): total_frontier_cells_blocked}
        self.blocking_counts: Dict[Tuple[int, int], int] = {}
        # {player_value: total_moves_made}
        self.move_counts: Dict[int, int] = {}

    def record_move(
        self,
        board_before: Board,
        board_after: Board,
        player: Player,
    ) -> Dict[int, int]:
        """Record blocking impact of a move.

        Args:
            board_before: Board state before the move.
            board_after: Board state after the move.
            player: Player who made the move.

        Returns:
            Dict mapping victim player values to number of frontier cells blocked.
        """
        pv = player.value
        self.move_counts[pv] = self.move_counts.get(pv, 0) + 1

        blocked: Dict[int, int] = {}
        for opponent in _PLAYERS:
            if opponent == player:
                continue
            ov = opponent.value
            frontier_before = board_before.get_frontier(opponent)
            frontier_after = board_after.get_frontier(opponent)
            lost = len(frontier_before) - len(frontier_after)
            if lost > 0:
                key = (pv, ov)
                self.blocking_counts[key] = self.blocking_counts.get(key, 0) + lost
                blocked[ov] = lost
        return blocked

    def get_blocking_rate(self, blocker: Player, victim: Player) -> float:
        """Fraction of blocker's moves that produced blocking against victim.

        Returns the average frontier cells blocked per move.
        """
        moves = self.move_counts.get(blocker.value, 0)
        if moves == 0:
            return 0.0
        blocked = self.blocking_counts.get((blocker.value, victim.value), 0)
        return blocked / moves

    def get_avg_blocking_rate(self, blocker: Player) -> float:
        """Average blocking rate across all opponents."""
        opponents = [p for p in _PLAYERS if p != blocker]
        if not opponents:
            return 0.0
        return sum(self.get_blocking_rate(blocker, v) for v in opponents) / len(opponents)

    def is_targeting(
        self, blocker: Player, victim: Player, threshold: float = 2.0
    ) -> bool:
        """Check if blocker is disproportionately targeting victim.

        Returns True if blocker's blocking rate against victim exceeds
        ``threshold`` times their average blocking rate against all opponents.
        Requires at least 3 moves to avoid false positives.
        """
        if self.move_counts.get(blocker.value, 0) < 3:
            return False
        avg = self.get_avg_blocking_rate(blocker)
        if avg <= 0:
            return False
        return self.get_blocking_rate(blocker, victim) > threshold * avg

    def reset(self) -> None:
        """Reset all tracking for a new game."""
        self.blocking_counts.clear()
        self.move_counts.clear()


# ---------------------------------------------------------------------------
# 7.2 — King-Maker Detection
# ---------------------------------------------------------------------------

class KingMakerDetector:
    """Detects late-game king-maker scenarios.

    A player is a potential king-maker when:
    1. The board is in the late phase (occupancy >= occupancy_threshold)
    2. Their score is far behind the leader (> score_gap_threshold)
    3. They still have legal moves (can influence the outcome)

    King-makers typically target the leader, so their moves should be
    modeled as anti-leader rather than self-maximizing.
    """

    def __init__(
        self,
        score_gap_threshold: int = 15,
        occupancy_threshold: float = 0.40,
    ) -> None:
        self.score_gap_threshold = score_gap_threshold
        self.occupancy_threshold = occupancy_threshold

    def get_board_occupancy(self, board: Board) -> float:
        """Fraction of board cells that are occupied."""
        import numpy as np

        total = board.SIZE * board.SIZE
        occupied = int(np.count_nonzero(board.grid))
        return occupied / total

    def detect(self, board: Board) -> Dict[Player, str]:
        """Classify each player's role in the current game state.

        Returns:
            Dict mapping each Player to one of:
            - ``"contender"``: competing for the win
            - ``"kingmaker"``: far behind but can influence outcome
            - ``"eliminated"``: no remaining frontier (cannot place)
        """
        occupancy = self.get_board_occupancy(board)
        if occupancy < self.occupancy_threshold:
            return {p: "contender" for p in _PLAYERS}

        scores = {p: board.get_score(p) for p in _PLAYERS}
        max_score = max(scores.values())

        roles: Dict[Player, str] = {}
        for p in _PLAYERS:
            frontier = board.get_frontier(p)
            if not frontier:
                roles[p] = "eliminated"
            elif max_score - scores[p] > self.score_gap_threshold:
                roles[p] = "kingmaker"
            else:
                roles[p] = "contender"
        return roles

    def get_leader(self, board: Board) -> Player:
        """Return the player with the highest score."""
        return max(_PLAYERS, key=lambda p: board.get_score(p))

    def get_likely_target(self, board: Board, kingmaker: Player) -> Optional[Player]:
        """King-makers typically target the leader.

        Returns the leader if they are not the kingmaker, else None.
        """
        leader = self.get_leader(board)
        if leader == kingmaker:
            return None
        return leader


# ---------------------------------------------------------------------------
# 7.3 — Adaptive Opponent Profile (Repeated Play)
# ---------------------------------------------------------------------------

@dataclass
class OpponentProfile:
    """Persistent model of an opponent built across multiple games.

    Updated after each completed game with statistics from that game's
    move history. During simulation, biases opponent move selection
    toward observed preferences.
    """

    # Running averages (initialised at neutral 0.5)
    avg_piece_size_preference: float = 0.5
    blocking_tendency: float = 0.5
    center_preference: float = 0.5
    games_observed: int = 0

    # Exponential moving average decay
    _ema_alpha: float = 0.3

    def update_from_game(
        self,
        total_moves: int,
        avg_piece_size: float,
        blocking_rate: float,
        center_proximity: float,
    ) -> None:
        """Update profile after a completed game.

        Args:
            total_moves: Number of moves the opponent made.
            avg_piece_size: Average piece size placed (normalised to [0, 1]).
            blocking_rate: Fraction of moves that blocked others.
            center_proximity: Normalised center proximity (0 = edge, 1 = center).
        """
        if total_moves == 0:
            return
        alpha = self._ema_alpha
        if self.games_observed == 0:
            # First game: initialise directly
            self.avg_piece_size_preference = avg_piece_size
            self.blocking_tendency = blocking_rate
            self.center_preference = center_proximity
        else:
            self.avg_piece_size_preference = (
                alpha * avg_piece_size + (1 - alpha) * self.avg_piece_size_preference
            )
            self.blocking_tendency = (
                alpha * blocking_rate + (1 - alpha) * self.blocking_tendency
            )
            self.center_preference = (
                alpha * center_proximity + (1 - alpha) * self.center_preference
            )
        self.games_observed += 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to dict for logging."""
        return {
            "avg_piece_size_preference": round(self.avg_piece_size_preference, 4),
            "blocking_tendency": round(self.blocking_tendency, 4),
            "center_preference": round(self.center_preference, 4),
            "games_observed": self.games_observed,
        }


# ---------------------------------------------------------------------------
# Manager — ties tracking, detection, and profiles together
# ---------------------------------------------------------------------------

class OpponentModelManager:
    """Central manager for opponent modeling during a game.

    Coordinates blocking tracking, alliance detection, king-maker awareness,
    and adaptive profiles for repeated play.
    """

    def __init__(
        self,
        root_player: Player,
        *,
        alliance_detection_enabled: bool = False,
        alliance_threshold: float = 2.0,
        kingmaker_detection_enabled: bool = False,
        kingmaker_score_gap: int = 15,
        adaptive_enabled: bool = False,
        defensive_weight_shift: float = 0.15,
    ) -> None:
        self.root_player = root_player
        self.alliance_detection_enabled = alliance_detection_enabled
        self.alliance_threshold = alliance_threshold
        self.kingmaker_detection_enabled = kingmaker_detection_enabled
        self.adaptive_enabled = adaptive_enabled
        self.defensive_weight_shift = defensive_weight_shift

        self.blocking_tracker = BlockingTracker()
        self.kingmaker_detector = KingMakerDetector(
            score_gap_threshold=kingmaker_score_gap,
        )

        # Per-opponent profiles for repeated play (keyed by player value)
        self.profiles: Dict[int, OpponentProfile] = {}

        # Cached flags updated after each move
        self._targeting_players: Set[int] = set()
        self._player_roles: Dict[Player, str] = {}

    def on_move_made(
        self,
        board_before: Board,
        board_after: Board,
        player: Player,
    ) -> None:
        """Called after each actual game move to update all tracking."""
        self.blocking_tracker.record_move(board_before, board_after, player)
        self._update_targeting_flags()

        if self.kingmaker_detection_enabled:
            self._player_roles = self.kingmaker_detector.detect(board_after)

    def _update_targeting_flags(self) -> None:
        """Refresh which opponents are flagged as targeting root player."""
        self._targeting_players.clear()
        if not self.alliance_detection_enabled:
            return
        for opp in _PLAYERS:
            if opp == self.root_player:
                continue
            if self.blocking_tracker.is_targeting(
                opp, self.root_player, self.alliance_threshold
            ):
                self._targeting_players.add(opp.value)

    def is_targeting_root(self, player: Player) -> bool:
        """Check if a player is flagged as targeting the root player."""
        return player.value in self._targeting_players

    def is_kingmaker(self, player: Player) -> bool:
        """Check if a player is in a king-maker role."""
        return self._player_roles.get(player) == "kingmaker"

    def get_role(self, player: Player) -> str:
        """Get the detected role for a player."""
        return self._player_roles.get(player, "contender")

    def get_opponent_rollout_policy(
        self, player: Player, default_policy: str
    ) -> str:
        """Determine rollout policy for an opponent player.

        If the opponent is targeting the root player, upgrade them to
        heuristic rollout for more realistic (pessimistic) simulations.
        If they are a king-maker, also use heuristic (models anti-leader play).

        Args:
            player: The opponent player.
            default_policy: The configured opponent rollout policy.

        Returns:
            The rollout policy string to use for this opponent.
        """
        if self.alliance_detection_enabled and self.is_targeting_root(player):
            return "heuristic"
        if self.kingmaker_detection_enabled and self.is_kingmaker(player):
            return "heuristic"
        return default_policy

    def get_defensive_eval_adjustment(self, board: Board) -> Dict[str, float]:
        """Return evaluation weight adjustments when under threat.

        When any opponent is targeting the root player, shift evaluation
        toward defensive features (accessible_corners, reachable_empty_squares)
        and away from aggressive features (squares_placed).

        Returns:
            Dict of weight deltas to add to base evaluation weights.
            Empty dict when no adjustment is needed.
        """
        if not self._targeting_players:
            return {}

        shift = self.defensive_weight_shift
        return {
            "accessible_corners": +shift,
            "reachable_empty_squares": +shift * 0.5,
            "squares_placed": -shift * 0.5,
            "opponent_avg_mobility": -shift * 0.5,
        }

    def get_profile(self, player: Player) -> OpponentProfile:
        """Get or create an opponent profile for repeated play."""
        pv = player.value
        if pv not in self.profiles:
            self.profiles[pv] = OpponentProfile()
        return self.profiles[pv]

    def reset_game(self) -> None:
        """Reset per-game state. Profiles persist across games."""
        self.blocking_tracker.reset()
        self._targeting_players.clear()
        self._player_roles.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics for logging/diagnostics."""
        stats: Dict[str, Any] = {
            "targeting_count": len(self._targeting_players),
            "targeting_players": sorted(self._targeting_players),
        }
        if self._player_roles:
            stats["roles"] = {p.name: r for p, r in self._player_roles.items()}

        # Blocking rates for root player
        for opp in _PLAYERS:
            if opp == self.root_player:
                continue
            rate = self.blocking_tracker.get_blocking_rate(opp, self.root_player)
            stats[f"blocking_rate_{opp.name}_vs_root"] = round(rate, 4)

        return stats

"""
Factory helpers for deploy-mode gameplay agent adapters.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from mcts.adaptive_budget import AdaptiveBudgetController, BudgetDecision, BudgetSignals
from mcts.champion_profile import (
    CHALLENGE_CHAMPION_PROFILE,
    build_mcts_kwargs,
    load_challenge_champion_profile,
)
from mcts.mcts_agent import MCTSAgent
from agents.gameplay_protocol import GameplayAgentProtocol
from engine.board import Board, Player
from engine.move_generator import Move
from schemas.game_state import AgentType


class _MCTSGameplayAdapter:
    """Wraps MCTSAgent to satisfy the GameplayAgentProtocol (choose_move)."""

    profile_name = "custom_mcts"

    def __init__(self, agent: MCTSAgent):
        self._agent = agent

    def choose_move(
        self,
        board: Board,
        player: Player,
        legal_moves: List[Move],
        budget_ms: int,
    ) -> Tuple[Optional[Move], Dict[str, Any]]:
        start = time.perf_counter()
        self._agent.time_limit = max(int(budget_ms), 1) / 1000.0
        move = self._agent.select_action(board, player, legal_moves)
        stats = _stats_from_agent(
            self._agent,
            budget_ms=int(budget_ms),
            elapsed_ms=int((time.perf_counter() - start) * 1000),
        )
        if hasattr(self._agent, 'get_search_trace'):
            trace = self._agent.get_search_trace()
            if trace:
                stats['searchTrace'] = trace
        return move, stats


class _ChallengeChampionGameplayAdapter(_MCTSGameplayAdapter):
    """Challenge profile adapter with deterministic adaptive per-move budgets."""

    profile_name = CHALLENGE_CHAMPION_PROFILE

    def __init__(
        self,
        *,
        seed: Optional[int] = None,
        max_budget_ms: Optional[int] = None,
        warmup_budget_ms: Optional[int] = None,
        tier_budgets_ms: Optional[Dict[str, int]] = None,
    ) -> None:
        self.profile = load_challenge_champion_profile()
        self.seed = seed
        self.max_budget_ms = int(max_budget_ms or self.profile["max_budget_ms"])
        self.warmup_budget_ms = int(warmup_budget_ms or self.profile["warmup_budget_ms"])
        self.tier_budgets_ms = dict(tier_budgets_ms or self.profile["tier_budgets_ms"])
        self.budget_controller = AdaptiveBudgetController(
            tier_budgets_ms=self.tier_budgets_ms,
            max_budget_ms=self.max_budget_ms,
        )
        self._agent = self._build_agent(time_limit_ms=self.tier_budgets_ms["normal"])

    def _build_agent(self, *, time_limit_ms: int) -> MCTSAgent:
        kwargs = build_mcts_kwargs(self.profile)
        kwargs["time_limit"] = max(int(time_limit_ms), 1) / 1000.0
        kwargs["seed"] = self.seed
        return MCTSAgent(**kwargs)

    def choose_move(
        self,
        board: Board,
        player: Player,
        legal_moves: List[Move],
        budget_ms: int,
    ) -> Tuple[Optional[Move], Dict[str, Any]]:
        start = time.perf_counter()
        if not legal_moves:
            decision = self.budget_controller.choose_budget(
                self._signals(board, player, legal_moves)
            )
            return None, self._empty_stats(decision, start)

        if len(legal_moves) == 1:
            decision = self.budget_controller.choose_budget(
                self._signals(board, player, legal_moves)
            )
            return legal_moves[0], self._empty_stats(decision, start)

        warmup_cap = min(self.warmup_budget_ms, self.max_budget_ms, max(int(budget_ms), 1))
        warmup_agent = self._build_agent(time_limit_ms=warmup_cap)
        warmup_move = warmup_agent.select_action(board, player, legal_moves)
        warmup_stats = _raw_agent_stats(warmup_agent)
        decision = self.budget_controller.choose_budget(
            self._signals(board, player, legal_moves, warmup_stats)
        )

        if decision.early_stop_reason and warmup_move is not None:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            stats = _stats_from_agent(warmup_agent, budget_ms=decision.budget_cap_ms, elapsed_ms=elapsed_ms)
            stats.update(_decision_stats(decision))
            return warmup_move, stats

        elapsed_before_final = int((time.perf_counter() - start) * 1000)
        remaining_budget = max(1, min(decision.budget_cap_ms, int(budget_ms), self.max_budget_ms) - elapsed_before_final)
        final_agent = self._build_agent(time_limit_ms=remaining_budget)
        self._agent = final_agent
        move = final_agent.select_action(board, player, legal_moves)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        stats = _stats_from_agent(final_agent, budget_ms=decision.budget_cap_ms, elapsed_ms=elapsed_ms)
        stats.update(_decision_stats(decision))
        return move, stats

    def _empty_stats(self, decision: BudgetDecision, start: float) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "timeBudgetMs": decision.budget_cap_ms,
            "timeSpentMs": int((time.perf_counter() - start) * 1000),
            "nodesEvaluated": 0,
            "iterations_run": 0,
            "maxDepthReached": 0,
            "topMoves": [],
        }
        stats.update(_decision_stats(decision))
        return stats

    def _signals(
        self,
        board: Board,
        player: Player,
        legal_moves: List[Move],
        warmup_stats: Optional[Dict[str, Any]] = None,
    ) -> BudgetSignals:
        scores = {pl: int(board.get_score(pl)) for pl in Player}
        player_score = scores[player]
        sorted_scores = sorted(scores.values(), reverse=True)
        score_rank = sorted_scores.index(player_score) + 1
        score_deficit = max(sorted_scores[0] - player_score, 0)
        occupied = int((board.grid != 0).sum())
        warmup_stats = warmup_stats or {}
        return BudgetSignals(
            legal_move_count=len(legal_moves),
            board_occupancy=occupied / float(board.SIZE * board.SIZE),
            score_deficit=score_deficit,
            score_rank=score_rank,
            regret_gap=warmup_stats.get("regret_gap"),
            visit_entropy=warmup_stats.get("visit_entropy"),
            best_move_stability=_best_move_stability(warmup_stats.get("topMoves") or []),
        )


def _best_move_stability(top_moves: List[Dict[str, Any]]) -> Optional[float]:
    if not top_moves:
        return None
    total_visits = sum(int(move.get("visits") or 0) for move in top_moves)
    if total_visits <= 0:
        return None
    best_visits = max(int(move.get("visits") or 0) for move in top_moves)
    return best_visits / total_visits


def _raw_agent_stats(agent: MCTSAgent) -> Dict[str, Any]:
    info = agent.get_action_info() if hasattr(agent, "get_action_info") else {}
    if not isinstance(info, dict):
        return {}
    stats = info.get("stats", {})
    return dict(stats) if isinstance(stats, dict) else {}


def _stats_from_agent(agent: MCTSAgent, *, budget_ms: int, elapsed_ms: int) -> Dict[str, Any]:
    raw = _raw_agent_stats(agent)
    iterations = int(raw.get("iterations_run") or 0)
    stats = dict(raw)
    stats["timeBudgetMs"] = int(budget_ms)
    stats["timeSpentMs"] = int(elapsed_ms)
    stats["nodesEvaluated"] = iterations
    stats["iterations_run"] = iterations
    stats["maxDepthReached"] = int(raw.get("tree_depth_max") or 0)
    stats["topMoves"] = list(raw.get("topMoves") or [])
    return stats


def _decision_stats(decision: BudgetDecision) -> Dict[str, Any]:
    return {
        "budgetTier": decision.tier,
        "budgetCapMs": decision.budget_cap_ms,
        "budgetReasons": list(decision.reasons),
        "earlyStopReason": decision.early_stop_reason,
    }


def build_deploy_gameplay_agent(
    agent_type: AgentType,
    agent_config: Optional[Dict[str, Any]] = None,
) -> Optional[GameplayAgentProtocol]:
    """
    Build gameplay adapters used by APP_PROFILE=deploy.

    Human players are returned as ``None`` because websocket drives those turns.
    """
    cfg = dict(agent_config or {})
    if agent_type == AgentType.HUMAN:
        return None
    if agent_type == AgentType.MCTS:
        if cfg.get("profile") == CHALLENGE_CHAMPION_PROFILE:
            return _ChallengeChampionGameplayAdapter(
                seed=cfg.get("seed"),
                max_budget_ms=cfg.get("max_budget_ms"),
                warmup_budget_ms=cfg.get("warmup_budget_ms"),
                tier_budgets_ms=cfg.get("tier_budgets_ms"),
            )
        agent = MCTSAgent(
            iterations=int(cfg.get("iterations", 5000)),
            exploration_constant=float(cfg.get("exploration_constant", 1.414)),
            time_limit=max(int(cfg.get("time_budget_ms", 1000)), 1) / 1000.0,
            seed=cfg.get("seed"),
        )
        return _MCTSGameplayAdapter(agent)
    raise ValueError(f"Unsupported deploy agent type: {agent_type}")


def is_gameplay_adapter(agent: Any) -> bool:
    return callable(getattr(agent, "choose_move", None)) and hasattr(type(agent), "choose_move")

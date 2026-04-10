"""
Factory helpers for deploy-mode gameplay agent adapters.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from mcts.mcts_agent import MCTSAgent
from agents.gameplay_protocol import GameplayAgentProtocol
from engine.board import Board, Player
from engine.move_generator import Move
from schemas.game_state import AgentType


class _MCTSGameplayAdapter:
    """Wraps MCTSAgent to satisfy the GameplayAgentProtocol (choose_move)."""

    def __init__(self, agent: MCTSAgent):
        self._agent = agent

    def choose_move(
        self,
        board: Board,
        player: Player,
        legal_moves: List[Move],
        budget_ms: int,
    ) -> Tuple[Optional[Move], Dict[str, Any]]:
        move = self._agent.select_action(board, player, legal_moves)
        stats: Dict[str, Any] = {}
        if hasattr(self._agent, 'get_search_trace'):
            trace = self._agent.get_search_trace()
            if trace:
                stats['searchTrace'] = trace
        if hasattr(self._agent, 'get_action_info'):
            info = self._agent.get_action_info()
            if 'stats' in info:
                stats.update(info['stats'])
        return move, stats


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
        agent = MCTSAgent(
            iterations=int(cfg.get("iterations", 5000)),
            exploration_constant=float(cfg.get("exploration_constant", 1.414)),
            seed=cfg.get("seed"),
        )
        return _MCTSGameplayAdapter(agent)
    raise ValueError(f"Unsupported deploy agent type: {agent_type}")


def is_gameplay_adapter(agent: Any) -> bool:
    return callable(getattr(agent, "choose_move", None))

import asyncio
import unittest
from unittest.mock import Mock

from engine.board import Player as EnginePlayer
from schemas.game_state import AgentType, GameConfig, Player, PlayerConfig
from webapi.app import GameManager


class TestChallengeGameplayStats(unittest.TestCase):
    def test_game_state_exposes_last_mcts_stats(self):
        async def run_test():
            manager = GameManager()
            game_id = "challenge_stats"
            config = GameConfig(
                game_id=game_id,
                players=[
                    PlayerConfig(player=Player.RED, agent_type=AgentType.MCTS),
                    PlayerConfig(player=Player.BLUE, agent_type=AgentType.HUMAN),
                ],
                auto_start=False,
            )
            manager.create_game(config)
            manager.games[game_id]["status"] = "in_progress"
            game = manager.games[game_id]["game"]
            legal_moves = game.get_legal_moves(EnginePlayer.RED)

            agent = Mock(spec=["select_action"])
            agent.select_action.return_value = legal_moves[0]
            manager.agent_instances[game_id][EnginePlayer.RED] = agent

            await manager._make_agent_move(game_id, EnginePlayer.RED, agent)
            state = manager._get_game_state(game_id)

            assert state.mcts_stats is not None
            assert state.mcts_stats["timeBudgetMs"] == 1000
            assert "timeSpentMs" in state.mcts_stats
            assert manager.games[game_id]["move_records"][-1]["stats"] == state.mcts_stats

        asyncio.run(run_test())

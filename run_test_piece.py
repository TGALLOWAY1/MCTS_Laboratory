import asyncio

from schemas.game_state import (
    AgentType,
    GameConfig,
    Move,
    MoveRequest,
    Player,
    PlayerConfig,
)
from webapi.app import GameManager


async def test_it():
    gm = GameManager()
    config = GameConfig(
        game_id="test_error",
        players=[
            PlayerConfig(player=Player.RED, agent_type=AgentType.HUMAN),
            PlayerConfig(player=Player.BLUE, agent_type=AgentType.RANDOM),
        ],
        auto_start=False
    )
    gm.create_game(config)

    move_request = MoveRequest(
        player=Player.RED,
        move=Move(piece_id=1, orientation=0, anchor_row=0, anchor_col=0)
    )
    res = await gm._process_human_move_immediately("test_error", move_request)
    print("SUCCESS?", res.success)
    print("MSG:", res.message)

asyncio.run(test_it())

import tzlocal
from typing import Annotated
from fastapi import APIRouter, Depends
from ..auth import basic_auth
from ..config import config
from ..scheduler import (
    get_tick_duration,
    get_first_tick_start,
    get_network_open_at_tick,
    get_game_ends_at_tick,
)

router = APIRouter(prefix="/connect", tags=["Connect"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/game")
async def enqueue(_: Annotated[str, Depends(basic_auth)]):
    return {
        "flag_format": config.game.flag_format,
        "team_ip": config.game.team_ip,
        "nop_team_ip": config.game.nop_team_ip or None,
    }


@router.get("/schedule")
async def schedule(_: Annotated[str, Depends(basic_auth)]):
    return {
        "first_tick_start": get_first_tick_start(),
        "tick_duration": get_tick_duration().total_seconds(),
        "network_open_tick": get_network_open_at_tick(),
        "total_ticks": get_game_ends_at_tick(),
        "tz": tzlocal.get_localzone_name(),
    }

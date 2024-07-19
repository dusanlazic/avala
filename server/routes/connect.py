import tzlocal
from datetime import datetime
from shared.logs import logger
from typing import Annotated
from fastapi import APIRouter, Depends
from server.auth import basic_auth
from server.config import config
from server.scheduler import (
    get_next_tick_start,
    get_tick_elapsed,
    get_tick_duration,
    get_first_tick_start,
    get_tick_number,
)

router = APIRouter(prefix="/connect", tags=["Connect"])


@router.get("/health")
async def health(_: Annotated[str, Depends(basic_auth)]):
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
    now = datetime.now()
    return {
        "tick_number": get_tick_number(),
        "first_tick_start": get_first_tick_start(),
        "next_tick_start": get_next_tick_start(now),
        "tick_elapsed": get_tick_elapsed(now),
        "tick_duration": get_tick_duration(),
        "tz": tzlocal.get_localzone_name(),
    }

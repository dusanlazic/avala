import tzlocal
from fastapi import APIRouter

from ..auth import CurrentUser
from ..config import AvalaConfig
from ..scheduler import (
    get_game_ends_at_tick,
    get_network_open_at_tick,
)

router = APIRouter(prefix="/connect", tags=["Connect"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/game")
async def enqueue(
    username: CurrentUser,
    config: AvalaConfig,
):
    return {
        "flag_format": config.game.flag_format,
        "team_ip": config.game.team_ip,
        "nop_team_ip": config.game.nop_team_ip,
    }


@router.get("/schedule")
async def schedule(
    username: CurrentUser,
    config: AvalaConfig,
):
    return {
        "first_tick_start": config.game.game_starts_at,
        "tick_duration": config.game.tick_duration.total_seconds(),
        "network_open_tick": get_network_open_at_tick(),
        "total_ticks": get_game_ends_at_tick(),
        "tz": tzlocal.get_localzone_name(),
    }

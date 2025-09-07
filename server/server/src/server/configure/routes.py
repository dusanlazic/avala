from avala.common.config import config
from fastapi import APIRouter, Depends

from server.auth import get_current_user

from .schemas import ConfigurationResponse, GameConfig, ScheduleConfig

router = APIRouter(prefix="/configure", tags=["configure"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=ConfigurationResponse)
async def get_config():
    """
    Get the server configuration for configuring clients.
    """
    return ConfigurationResponse(
        game=GameConfig(
            flag_format=config.game.flag_format,
            own_team_hosts=config.game.own_team_hosts,
            nop_team_hosts=config.game.nop_team_hosts,
            opp_team_hosts=config.game.opp_team_hosts,
        ),
        schedule=ScheduleConfig(
            first_tick_start=config.game.game_starts_at,
            tick_duration=config.game.tick_duration.total_seconds(),
            network_open_tick=config.game.networks_open_after // config.game.tick_duration,
            total_ticks=config.game.game_ends_after // config.game.tick_duration,
        ),
    )

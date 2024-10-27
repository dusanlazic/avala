from datetime import datetime

from pydantic import BaseModel, PositiveFloat, PositiveInt


class GameResponse(BaseModel):
    flag_format: str
    team_ip: list[str]
    nop_team_ip: list[str]


class ScheduleResponse(BaseModel):
    first_tick_start: datetime
    tick_duration: PositiveFloat
    network_open_tick: PositiveInt
    total_ticks: PositiveInt
    tz: str

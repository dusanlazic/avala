from pydantic import AwareDatetime, BaseModel, PositiveFloat, PositiveInt


class GameConfig(BaseModel):
    flag_format: str
    own_team_hosts: set[str]
    nop_team_hosts: set[str]
    opp_team_hosts: set[str]


class ScheduleConfig(BaseModel):
    first_tick_start: AwareDatetime
    tick_duration: PositiveFloat  # may use timedelta?
    network_open_tick: PositiveInt
    total_ticks: PositiveInt


class ConfigurationResponse(BaseModel):
    game: GameConfig
    schedule: ScheduleConfig

import yaml
from typing import Annotated
from fastapi import Depends
from pathlib import Path
from pydantic import (
    BaseModel,
    Field,
    NonNegativeInt,
    PositiveInt,
    PositiveFloat,
    field_validator,
    model_validator,
    ConfigDict,
    ValidationError,
)
from datetime import datetime, timedelta
from .shared.logs import logger


DOT_DIR_PATH = Path(".avala")


class TimeDeltaConfig(BaseModel):
    hours: NonNegativeInt = 0
    minutes: NonNegativeInt = 0
    seconds: NonNegativeInt = 0

    @model_validator(mode="before")
    def ensure_at_least_one(cls, v):
        if not any(v):
            raise ValueError("At least one of hours, minutes or seconds must be set.")
        return v

    @model_validator(mode="after")
    def to_timedelta(cls, values):
        return timedelta(
            hours=values.hours or 0,
            minutes=values.minutes or 0,
            seconds=values.seconds or 0,
        )

    model_config = ConfigDict(extra="forbid")


class GameConfig(BaseModel):
    tick_duration: timedelta
    flag_format: str
    team_ip: list[str]
    nop_team_ip: list[str]
    flag_ttl: PositiveInt | None = None
    game_starts_at: datetime
    networks_open_after: TimeDeltaConfig
    game_ends_after: TimeDeltaConfig

    @field_validator("team_ip", "nop_team_ip", mode="before")
    def ensure_list(cls, v):
        return v if isinstance(v, list) else [v]

    model_config = ConfigDict(extra="forbid")


class SubmitterConfig(BaseModel):
    module: str = "subimtter"
    interval: PositiveInt | None = None
    per_tick: PositiveInt | None = None
    batch_size: PositiveInt | None = None
    max_batch_size: int | None = None
    streams: bool | None = False

    @model_validator(mode="before")
    def check_required_fields(cls, values):
        one_of = [
            {"interval", "max_batch_size"},
            {"per_tick", "max_batch_size"},
            {"batch_size"},
            {"streams"},
        ]

        for fields in one_of:
            if all(values.get(field) is not None for field in fields):
                return values

        raise ValueError(
            f"One of the following groups of fields must be present and non-null: {one_of}"
        )

    @model_validator(mode="after")
    def set_max_batch_size(cls, values):
        if values.max_batch_size is not None and values.max_batch_size < 1:
            values.max_batch_size = float("inf")
        return values

    model_config = ConfigDict(extra="forbid")


class AttackDataConfig(BaseModel):
    module: str = "flag_ids"
    max_attempts: PositiveInt = 5
    retry_interval: PositiveFloat = 2

    model_config = ConfigDict(extra="forbid")


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(2024, ge=1, le=65535)
    password: str | None = None
    cors: list[str] = []
    frontend: bool = True

    model_config = ConfigDict(extra="forbid")


class DatabaseConfig(BaseModel):
    name: str
    user: str
    password: str
    host: str
    port: int = Field(5432, ge=1, le=65535)

    model_config = ConfigDict(extra="forbid")

    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RabbitMQConfig(BaseModel):
    user: str
    password: str
    host: str
    port: int = Field(5672, ge=1, le=65535)
    management_port: int = Field(15672, ge=1, le=65535)

    model_config = ConfigDict(extra="forbid")

    def dsn(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/"


class Config(BaseModel):
    game: GameConfig
    server: ServerConfig
    submitter: SubmitterConfig
    attack_data: AttackDataConfig
    database: DatabaseConfig
    rabbitmq: RabbitMQConfig


config: Config = None


def load_user_config():
    global config

    # Remove datetime resolver
    # https://stackoverflow.com/a/52312810
    yaml.SafeLoader.yaml_implicit_resolvers = {
        k: [r for r in v if r[0] != "tag:yaml.org,2002:timestamp"]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    for ext in ["yml", "yaml"]:
        if Path(f"server.{ext}").is_file():
            with open(f"server.{ext}", "r") as file:
                try:
                    config_data = yaml.safe_load(file)
                    if not config_data:
                        logger.error(
                            "No configuration found in server.{ext}. Exiting...",
                            ext=ext,
                        )
                        exit(1)

                    config = Config(**config_data)
                    logger.info("Loaded user configuration.")
                except ValidationError as e:
                    logger.error("Errors found in server.{ext}: {e}", ext=ext, e=e)
                    exit(1)
                except Exception as e:
                    logger.error("Error loading server.{ext}: {e}", ext=ext, e=e)
                    exit(1)
                break
    else:
        logger.error(
            "server.yaml/.yml not found in the current working directory. Exiting..."
        )
        exit(1)


def get_config() -> Config:
    if config is None:
        load_user_config()
    return config


async def get_config_async() -> Config:
    return get_config()


AvalaConfig = Annotated[Config, Depends(get_config_async)]

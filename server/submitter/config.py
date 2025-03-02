from datetime import datetime, timedelta
from typing import Any, Type

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource

from logger import logger


class GameConfig(BaseModel):
    tick_duration: timedelta
    flag_format: str
    own_team_hosts: set[str]
    opp_team_hosts: set[str]
    nop_team_hosts: set[str] = Field(default_factory=set)
    flag_ttl: timedelta
    game_starts_at: datetime
    networks_open_after: timedelta
    game_ends_after: timedelta

    @field_validator("own_team_hosts", "opp_team_hosts", "nop_team_hosts", mode="before")
    def ensure_set(cls, v):
        return v if isinstance(v, set) else set(v)

    model_config = ConfigDict(extra="forbid")


class SubmitterConfig(BaseModel):
    module: str = Field(default="submitter")
    retries: PositiveInt = Field(default=5)
    interval: timedelta | None = Field(default=None)
    per_tick: PositiveInt | None = Field(default=None)
    batch_size: PositiveInt | None = Field(default=None)
    workers: PositiveInt | None = Field(default=None)

    @model_validator(mode="before")
    def check_required_fields(cls, values):
        allowed_field_sets = [
            {"interval", "batch_size"},
            {"per_tick", "batch_size"},
            {"batch_size"},
            {"workers"},
        ]
        all_fields = set().union(*allowed_field_sets)

        for field_set in allowed_field_sets:
            if all(values.get(field) is not None for field in field_set) and all(
                values.get(field) is None for field in all_fields - field_set
            ):
                return values

        raise ValueError(f"One of the following groups of fields must be present and non-null: {allowed_field_sets}")

    model_config = ConfigDict(extra="forbid")


class AttackDataConfig(BaseModel):
    module: str = Field(default="flag_ids")
    retries: PositiveInt = Field(default=5)
    interval: timedelta = Field(default=timedelta(seconds=2))

    model_config = ConfigDict(extra="forbid")


class APIConfig(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: PositiveInt = Field(default=2024)
    password: str | None = Field(default=None)
    cors: set[str] = Field(default_factory=set)
    dashboard: bool = Field(default=True)

    model_config = ConfigDict(extra="forbid")


class PostgresConfig(BaseModel):
    name: str
    user: str
    password: str
    host: str
    port: int = Field(default=5432, ge=1, le=65535)

    model_config = ConfigDict(extra="forbid")


class RabbitMQConfig(BaseModel):
    user: str
    password: str
    host: str
    port: int = Field(default=5672, ge=1, le=65535)
    management_port: int = Field(default=15672, ge=1, le=65535)

    model_config = ConfigDict(extra="forbid")


class AvalaServerConfig(BaseSettings):
    game: GameConfig
    submitter: SubmitterConfig
    server: APIConfig
    attack_data: AttackDataConfig
    database: PostgresConfig
    rabbitmq: RabbitMQConfig

    model_config = SettingsConfigDict(
        extra="ignore",
        yaml_file=[
            "avala.yaml",
            "avala.yml",
        ],
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls: Type[BaseSettings], **kwargs: Any):  # type: ignore
        return (YamlConfigSettingsSource(settings_cls),)


def load_config() -> AvalaServerConfig:
    try:
        return AvalaServerConfig()  # type: ignore
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            error_path = ".".join(error["loc"])  # type: ignore
            error_messages.append("Error in %s\n\t%s\n" % (error_path, error["msg"]))

        logger.error(
            "Configuration validation failed:\n{error_messages}",
            error_messages="\n".join(error_messages),
        )
        exit(1)


config = load_config()

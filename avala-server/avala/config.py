from datetime import datetime, timedelta
from pathlib import Path

from avala_shared.logs import logger
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

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
        # TODO: Find a better way to convert this to a timedelta to fix mypy errors.
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
    flag_ttl: PositiveInt
    game_starts_at: datetime
    networks_open_after: TimeDeltaConfig
    game_ends_after: TimeDeltaConfig

    @field_validator("team_ip", "nop_team_ip", mode="before")
    def ensure_list(cls, v):
        return v if isinstance(v, list) else [v]

    model_config = ConfigDict(extra="forbid")


class SubmitterConfig(BaseModel):
    module: str = "submitter"
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

    def dsn(self, driver: str = "") -> str:
        return f"postgresql{'+' if driver else ''}{driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RabbitMQConfig(BaseModel):
    user: str
    password: str
    host: str
    port: int = Field(5672, ge=1, le=65535)
    management_port: int = Field(15672, ge=1, le=65535)

    model_config = ConfigDict(extra="forbid")

    def dsn(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/"


class AvalaConfig(BaseSettings):
    game: GameConfig
    server: ServerConfig
    submitter: SubmitterConfig
    attack_data: AttackDataConfig
    database: DatabaseConfig
    rabbitmq: RabbitMQConfig

    model_config = SettingsConfigDict(
        extra="forbid",
        yaml_file=["server.yaml", "server.yml"],
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: BaseSettings,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (YamlConfigSettingsSource(settings_cls),)  # type: ignore[arg-type]


try:
    config: AvalaConfig = AvalaConfig()  # type: ignore[call-arg]
except ValidationError as e:
    error_messages = []
    for error in e.errors():
        error_path = ".".join(error["loc"])
        error_messages.append("Error in %s\n\t%s\n" % (error_path, error["msg"]))

    logger.error(
        "Configuration validation failed:\n{error_messages}",
        error_messages="\n".join(error_messages),
    )
    exit(1)

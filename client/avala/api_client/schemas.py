import hashlib
import json
from datetime import timedelta
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, Field, PositiveInt
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer


class GameConfig(BaseModel):
    flag_format: str
    team_ip: list[str]
    nop_team_ip: list[str]


class ScheduleConfig(BaseModel):
    first_tick_start: AwareDatetime
    tick_duration: timedelta
    network_open_tick: PositiveInt
    total_ticks: PositiveInt


class ConnectionConfig(BaseModel):
    protocol: Literal["http", "https"] = "http"
    host: str = "localhost"
    port: int = Field(ge=1, le=65535, default=2024)
    username: str = Field(max_length=20, default="anon")
    password: str | None = None


class CachedConfig(BaseModel):
    connection: ConnectionConfig
    game: GameConfig
    schedule: ScheduleConfig


class TickScopedAttackData:
    """
    Attack data specific to a single service and target, and a single tick.
    """

    def __init__(
        self,
        flag_ids: Any,
    ):
        self.flag_ids: Any = flag_ids

    @classmethod
    def hash_flag_ids(cls, alias: str, target: str, flag_ids: Any) -> str:
        """
        Hashes the specific flag ID in order to track it to ensure that the same attack is not executed multiple times.

        :return: Hash computed from the alias, target, and flag IDs.
        :rtype: str
        """
        return hashlib.md5((alias + target + str(flag_ids)).encode()).hexdigest()

    def serialize(self) -> Any:
        return self.flag_ids

    def __repr__(self) -> str:
        json_string = json.dumps(self.serialize(), indent=4)
        return highlight(json_string, JsonLexer(), TerminalFormatter())


class TargetScopedAttackData:
    """
    Attack data specific to a single service and target, covering the last N ticks as provided by the game server.
    """

    def __init__(
        self,
        ticks: list[Any],
    ):
        self.ticks: list[TickScopedAttackData] = [
            TickScopedAttackData(flag_ids) for flag_ids in ticks
        ]

    def serialize(self) -> list[Any]:
        return [tick.serialize() for tick in self.ticks]

    def get_flag_ids_for_tick(self, index: int) -> Any:
        """
        Returns the attack data for a specific tick.

        :param index: Index of the tick.
        :type index: int
        :return: Attack data for the specified tick.
        :rtype: TickScopedAttackData
        :raises IndexError: If the tick index is out of range.
        """
        if 0 <= index < len(self.ticks):
            return self.ticks[index].flag_ids
        else:
            raise IndexError(f"Tick index '{index}' out of range")

    def __truediv__(self, index: int) -> Any:
        return self.get_flag_ids_for_tick(index)

    def __getitem__(self, index: int) -> Any:
        return self.get_flag_ids_for_tick(index)

    def __repr__(self) -> str:
        json_string = json.dumps(self.serialize(), indent=4)
        return highlight(json_string, JsonLexer(), TerminalFormatter())


class ServiceScopedAttackData:
    """
    Attack data specific to a single service, covering all `up` targets as provided by the game server.
    """

    def __init__(
        self,
        targets: dict[str, list[Any]],
    ):
        self.targets: dict[str, TargetScopedAttackData] = {
            target: TargetScopedAttackData(ticks) for target, ticks in targets.items()
        }

    def serialize(self) -> dict[str, list[Any]]:
        return {target: ticks.serialize() for target, ticks in self.targets.items()}

    def get_targets(self) -> list[str]:
        """
        Returns a list of all targets for which attack data is available.

        :return: List of IP addresses or hostnames of the teams.
        :rtype: list[str]
        """
        return list(self.targets.keys())

    def get_flag_ids_for_target(self, target: str) -> TargetScopedAttackData:
        """
        Returns the attack data for a specific target.

        :param target: IP address or hostname of the target/victim team.
        :type target: str
        :return: Attack data for the specified target.
        :rtype: TargetScopedAttackData
        :raises KeyError: If the target is not found.
        """
        if target in self.targets:
            return self.targets[target]
        else:
            raise KeyError(f"Target '{target}' not found")

    def __truediv__(self, target: str) -> TargetScopedAttackData:
        return self.get_flag_ids_for_target(target)

    def __getitem__(self, target: str) -> TargetScopedAttackData:
        return self.get_flag_ids_for_target(target)

    def __repr__(self) -> str:
        json_string = json.dumps(self.serialize(), indent=4)
        return highlight(json_string, JsonLexer(), TerminalFormatter())


class UnscopedAttackData:
    """
    Attack data covering all services provided by the game server.
    """

    def __init__(self, data: dict[str, dict[str, list[Any]]]):
        self.services: dict[str, ServiceScopedAttackData] = {
            service: ServiceScopedAttackData(targets)
            for service, targets in data.items()
        }

    def serialize(
        self,
    ) -> dict[
        str,
        dict[str, list[Any]],
    ]:
        return {service: data.serialize() for service, data in self.services.items()}

    def get_services(self) -> list[str]:
        """
        Returns a list of all services for which attack data is available.

        :return: List of service names.
        :rtype: list[str]
        """
        return list(self.services.keys())

    def get_flag_ids_for_service(self, service: str) -> ServiceScopedAttackData:
        """
        Returns the attack data for a specific service and all its targets.

        :param service: Name of the service.
        :type service: str
        :return: Attack data for the specified service.
        :rtype: ServiceScopedAttackData
        :raises KeyError: If the service is not found.
        """
        if service in self.services:
            return self.services[service]
        else:
            raise KeyError(f"Service '{service}' not found")

    def __truediv__(self, service: str) -> ServiceScopedAttackData:
        return self.get_flag_ids_for_service(service)

    def __getitem__(self, service: str) -> ServiceScopedAttackData:
        return self.get_flag_ids_for_service(service)

    def __repr__(self) -> str:
        json_string = json.dumps(self.serialize(), indent=4)
        return highlight(json_string, JsonLexer(), TerminalFormatter())

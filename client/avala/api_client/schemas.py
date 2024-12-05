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
    own_team_hosts: set[str]
    nop_team_hosts: set[str]


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


class EnqueueBody(BaseModel):
    values: list[str]
    exploit: str
    target: str


class FlagEnqueueResponse(BaseModel):
    enqueued: int
    discarded: int


class TickScopedFlagIds:
    """
    Flag ids for a specific tick of a target within a service, as provided by the game
    server.
    """

    def __init__(
        self,
        service: str,
        target: str,
        ticks_ago: int,
        flag_ids: Any,
    ):
        self._validate(service, target, ticks_ago, flag_ids)
        self.service: str = service
        self.target: str = target
        self.ticks_ago: int = ticks_ago
        self.flag_ids: Any = flag_ids

    @classmethod
    def hash_flag_ids(cls, alias: str, target: str, flag_ids: Any) -> str:
        """
        Hashes the specific flag ID in order to track it to ensure that the same attack
        is not executed multiple times.

        :return: Hash computed from the alias, target, and flag IDs.
        :rtype: str
        """
        return hashlib.md5((alias + target + str(flag_ids)).encode()).hexdigest()

    def serialize(self) -> Any:
        return self.flag_ids

    @staticmethod
    def _validate(service: Any, target: Any, ticks_ago: Any, flag_ids: Any) -> None:
        if not isinstance(service, str):
            raise ValueError("Service name must be a string." + f" Got {type(service).__name__} ('{service}').")
        if not isinstance(target, str):
            raise ValueError("Target name must be a string." + f" Got {type(target).__name__} ('{target}').")
        if not isinstance(ticks_ago, int):
            raise ValueError(
                "Ticks ago value must be an integer." + f" Got {type(ticks_ago).__name__} ('{ticks_ago}')."
            )
        if not isinstance(flag_ids, list):
            raise ValueError(
                f"Flag IDs for the service '{service}' and target '{target}' and tick {ticks_ago} must be a list."
                + f" Got {type(flag_ids).__name__} ('{flag_ids}')."
            )

    def __repr__(self) -> str:
        json_string = json.dumps(self.serialize(), indent=4)
        return highlight(json_string, JsonLexer(), TerminalFormatter())


class TargetScopedFlagIds:
    """
    Flag ids for all ticks of a specific target within a service, as provided by the
    game server.
    """

    def __init__(
        self,
        service: str,
        target: str,
        ticks: list[Any],
    ):
        self._validate(service, target, ticks)
        self.service: str = service
        self.target: str = target
        self.ticks: list[TickScopedFlagIds] = [
            TickScopedFlagIds(service, target, ticks_ago, flag_ids) for ticks_ago, flag_ids in enumerate(ticks)
        ]

    def serialize(self) -> list[Any]:
        return [tick.serialize() for tick in self.ticks]

    def get_flag_ids_for_tick(self, index: int) -> Any:
        """
        Returns the flag ids for a specific tick.

        :param index: Index of the tick.
        :type index: int
        :return: Flag ids for the specified tick.
        :rtype: TickScopedFlagIds
        :raises IndexError: If the tick index is out of range.
        """
        if 0 <= index < len(self.ticks):
            return self.ticks[index].flag_ids
        else:
            raise IndexError(f"Tick index '{index}' out of range")

    @staticmethod
    def _validate(service: Any, target: Any, ticks: Any) -> None:
        if not isinstance(service, str):
            raise ValueError("Service name must be a string." + f" Got {type(service).__name__} ('{service}').")
        if not isinstance(target, str):
            raise ValueError("Target name must be a string." + f" Got {type(target).__name__} ('{target}').")
        if not isinstance(ticks, list):
            raise ValueError(
                f"Flag IDs for the service '{service}' and target '{target}' must be a list."
                + f" Got {type(ticks).__name__} ('{ticks}')."
            )

    def __truediv__(self, index: int) -> Any:
        return self.get_flag_ids_for_tick(index)

    def __getitem__(self, index: int) -> Any:
        return self.get_flag_ids_for_tick(index)

    def __repr__(self) -> str:
        json_string = json.dumps(self.serialize(), indent=4)
        return highlight(json_string, JsonLexer(), TerminalFormatter())


class ServiceScopedFlagIds:
    """
    Flag ids for all targets of a specific service, covering the last N ticks as
    provided by the game server.
    """

    def __init__(
        self,
        service: str,
        targets: dict[str, list[Any]],
    ):
        self._validate(service, targets)
        self.service: str = service
        self.targets: dict[str, TargetScopedFlagIds] = {
            target: TargetScopedFlagIds(service, target, ticks) for target, ticks in targets.items()
        }

    def serialize(self) -> dict[str, list[Any]]:
        return {target: ticks.serialize() for target, ticks in self.targets.items()}

    def get_target_hosts(self) -> set[str]:
        """
        Returns a set of all targets for which flag ids are available.

        :return: Set of IP addresses or hostnames of the teams.
        :rtype: set[str]
        """
        return set(self.targets.keys())

    def get_flag_ids_for_target(self, target: str) -> TargetScopedFlagIds:
        """
        Returns the flag ids for a specific target.

        :param target: IP address or hostname of the target/victim team.
        :type target: str
        :return: Flag ids for the specified target.
        :rtype: TargetScopedFlagIds
        :raises KeyError: If the target is not found.
        """
        if target in self.targets:
            return self.targets[target]
        else:
            raise KeyError(f"Target '{target}' not found")

    @staticmethod
    def _validate(service: Any, targets: Any) -> None:
        if not isinstance(service, str):
            raise ValueError("Service name must be a string." + f"Got {type(service).__name__} ('{service}').")
        if not isinstance(targets, dict):
            raise ValueError(
                f"Flag IDs of the service '{service}' must be a dictionary."
                + f" Got {type(targets).__name__} ('{targets}')."
            )

    def __truediv__(self, target: str) -> TargetScopedFlagIds:
        return self.get_flag_ids_for_target(target)

    def __getitem__(self, target: str) -> TargetScopedFlagIds:
        return self.get_flag_ids_for_target(target)

    def __repr__(self) -> str:
        json_string = json.dumps(self.serialize(), indent=4)
        return highlight(json_string, JsonLexer(), TerminalFormatter())


class UnscopedFlagIds:
    """
    Flag ids for all targets across all services, covering the last N ticks as
    provided by the game server.
    """

    def __init__(self, data: dict[str, dict[str, list[Any]]]):
        self._validate(data)
        self.services: dict[str, ServiceScopedFlagIds] = {
            service: ServiceScopedFlagIds(service, targets) for service, targets in data.items()
        }

    def serialize(self) -> dict[str, dict[str, list[Any]]]:
        return {service: data.serialize() for service, data in self.services.items()}

    def get_service_names(self) -> list[str]:
        """
        Returns a list of all service names for which flag ids are available.

        :return: List of service names.
        :rtype: list[str]
        """
        return list(self.services.keys())

    def get_flag_ids_for_service(self, service: str) -> ServiceScopedFlagIds:
        """
        Returns the flag ids for a specific service and all its targets.

        :param service: Name of the service.
        :type service: str
        :return: Flag ids for the specified service.
        :rtype: ServiceScopedFlagIds
        :raises KeyError: If the service is not found.
        """
        if service in self.services:
            return self.services[service]
        else:
            raise KeyError(f"Service '{service}' not found")

    @staticmethod
    def _validate(data: Any) -> None:
        if not isinstance(data, dict):
            raise ValueError("Flag IDs must be a dictionary.")

    def __truediv__(self, service: str) -> ServiceScopedFlagIds:
        return self.get_flag_ids_for_service(service)

    def __getitem__(self, service: str) -> ServiceScopedFlagIds:
        return self.get_flag_ids_for_service(service)

    def __repr__(self) -> str:
        json_string = json.dumps(self.serialize(), indent=4)
        return highlight(json_string, JsonLexer(), TerminalFormatter())

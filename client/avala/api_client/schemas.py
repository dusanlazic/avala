import hashlib
from datetime import timedelta
from typing import Any, Iterator, Literal

from pydantic import AwareDatetime, BaseModel, Field, PositiveInt


class GameConfig(BaseModel):
    flag_format: str
    own_team_hosts: set[str]
    nop_team_hosts: set[str]
    opp_team_hosts: set[str]


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


class FlagsEnqueueBody(BaseModel):
    values: set[str]
    host: str
    worker: str
    service: str | None = None
    exploit: str | None = None


class FlagsEnqueueResponse(BaseModel):
    enqueued: int
    discarded: int


class TickScopedFlagIds:
    """
    Flag IDs for a particular service, target and a tick as provided by the game server.
    """

    def __init__(
        self,
        service_name: str,
        target_host: str,
        ticks_ago: int,
        flag_ids: Any,
    ):
        self._validate(service_name, target_host, ticks_ago)
        self.service_name: str = service_name
        self.target_host: str = target_host
        self.ticks_ago: int = ticks_ago
        self.value: Any = flag_ids

    def compute_hash(self, exploit_alias: str) -> str:
        """
        Hashes the specific flag ID in order to track it to ensure that the same attack
        is not executed multiple times.

        :return: Hash computed from the alias, target, and flag IDs.
        :rtype: str
        """
        return hashlib.md5((exploit_alias + self.target_host + str(self.value)).encode()).hexdigest()

    @staticmethod
    def _validate(service_name: Any, target_host: Any, ticks_ago: Any) -> None:
        if not isinstance(service_name, str):
            raise ValueError(
                "Service name must be a string." + f" Got {type(service_name).__name__} ('{service_name}')."
            )
        if not isinstance(target_host, str):
            raise ValueError("Target host must be a string." + f" Got {type(target_host).__name__} ('{target_host}').")
        if not isinstance(ticks_ago, int):
            raise ValueError(
                "Ticks ago value must be an integer." + f" Got {type(ticks_ago).__name__} ('{ticks_ago}')."
            )


class TargetScopedFlagIds:
    """
    Flag IDs for a particular service and target, and last N ticks provided by the game server. Allows traversing the
    flag IDs structure in a intuitive way.

    Example:
        Using `/` operator you can reduce the scope of the flag IDs to a specific tick. The class hierarchy is as
        follows:

            `UnscopedFlagIds` -> `ServiceScopedFlagIds` -> `TargetScopedFlagIds` -> `TickScopedFlagIds` -> `Any`

        The following example demonstrates how to access flag IDs for a specific service, target, and tick:

        .. code-block:: python

            foo_13_flag_ids: TargetScopedFlagIds  # Flag IDs for the service 'foo' and target '10.10.13.37'
            flag_ids: Any = foo_13_flag_ids / 0   # Flag IDs of the latest tick
    """

    def __init__(
        self,
        service_name: str,
        target_host: str,
        ticks_data: list[Any],
    ):
        self._validate(service_name, target_host, ticks_data)
        self.service_name: str = service_name
        self.target_host: str = target_host
        self.ticks: list[TickScopedFlagIds] = [
            TickScopedFlagIds(service_name, target_host, ticks_ago, flag_ids)
            for ticks_ago, flag_ids in enumerate(ticks_data)
        ]

    def serialize(self) -> list[Any]:
        return [tick.value for tick in self.ticks]

    def get_flag_ids_for_tick(self, index: int) -> TickScopedFlagIds:
        """
        Returns the flag ids for a specific tick.

        :param index: Index of the tick.
        :type index: int
        :return: Flag ids for the specified tick.
        :rtype: TickScopedFlagIds
        :raises IndexError: If the tick index is out of range.
        """
        if 0 <= index < len(self.ticks):
            return self.ticks[index]
        else:
            raise IndexError(f"Tick index '{index}' out of range")

    def walk(self) -> Iterator[TickScopedFlagIds]:
        for tick in self.ticks:
            yield tick

    def copy(self) -> "TargetScopedFlagIds":
        """
        Creates a deep copy of the flag IDs.

        :return: A deep copy of the flag IDs.
        :rtype: TargetScopedFlagIds
        """
        return TargetScopedFlagIds(self.service_name, self.target_host, self.serialize())

    @staticmethod
    def _validate(service_name: Any, target_host: Any, ticks_data: Any) -> None:
        if not isinstance(service_name, str):
            raise ValueError(
                "Service name must be a string." + f" Got {type(service_name).__name__} ('{service_name}')."
            )
        if not isinstance(target_host, str):
            raise ValueError("Target host must be a string." + f" Got {type(target_host).__name__} ('{target_host}').")
        if not isinstance(ticks_data, list):
            raise ValueError(
                f"Flag IDs for the service '{service_name}' and target '{target_host}' must be a list."
                + f" Got {type(ticks_data).__name__} ('{ticks_data}')."
            )

    def __truediv__(self, index: int) -> Any:
        return self.get_flag_ids_for_tick(index)

    def __getitem__(self, index: int) -> Any:
        return self.get_flag_ids_for_tick(index)


class ServiceScopedFlagIds:
    """
    Flag IDs for a particular service, its targets, and last N ticks provided by the game server. Allows traversing the
    flag IDs structure in a intuitive way.

    Example:
        Using `/` operator you can reduce the scope of the flag IDs to a specific target or tick. The class
        hierarchy is as follows:

            `UnscopedFlagIds` -> `ServiceScopedFlagIds` -> `TargetScopedFlagIds` -> `TickScopedFlagIds` -> `Any`

        The following example demonstrates how to access flag IDs for a specific service, target, and tick:

        .. code-block:: python

            foo_flag_ids: ServiceScopedFlagIds
            flag_ids: Any = foo_flag_ids / "10.10.13.37" / 0
    """

    def __init__(
        self,
        service_name: str,
        targets_data: dict[str, list[Any]],
    ):
        self._validate(service_name, targets_data)
        self.service_name: str = service_name
        self.targets: set[TargetScopedFlagIds] = {
            TargetScopedFlagIds(service_name, target_host, ticks_data)
            for target_host, ticks_data in targets_data.items()
        }

        self._target_host_map: dict[str, TargetScopedFlagIds] = {target.target_host: target for target in self.targets}

    def serialize(self) -> dict[str, list[Any]]:
        return {target.target_host: target.serialize() for target in self.targets}

    def get_target_hosts(self) -> set[str]:
        """
        Returns a set of all targets for which flag ids are available.

        :return: Set of IP addresses or hostnames of the targets.
        :rtype: set[str]
        """
        return set(self._target_host_map.keys())

    def get_flag_ids_for_target(self, target_host: str) -> TargetScopedFlagIds:
        """
        Returns the flag ids for a specific target.

        :param target_host: IP address or hostname of the target/victim team.
        :type target_host: str
        :return: Flag ids for the specified target.
        :rtype: TargetScopedFlagIds
        :raises KeyError: If the target is not found.
        """
        if target_host in self._target_host_map:
            return self._target_host_map[target_host]
        else:
            raise KeyError(f"Target '{target_host}' not found")

    def walk(self) -> Iterator[TickScopedFlagIds]:
        for target in self.targets:
            yield from target.walk()

    def copy(self) -> "ServiceScopedFlagIds":
        """
        Creates a deep copy of the flag IDs.

        :return: A deep copy of the flag IDs.
        :rtype: ServiceScopedFlagIds
        """
        return ServiceScopedFlagIds(self.service_name, self.serialize())

    @staticmethod
    def _validate(service_name: Any, targets_data: Any) -> None:
        if not isinstance(service_name, str):
            raise ValueError(
                "Service name must be a string." + f"Got {type(service_name).__name__} ('{service_name}')."
            )
        if not isinstance(targets_data, dict):
            raise ValueError(
                f"Flag IDs of the service '{service_name}' must be a dictionary."
                + f" Got {type(targets_data).__name__} ('{targets_data}')."
            )

    def __truediv__(self, target_host: str) -> TargetScopedFlagIds:
        return self.get_flag_ids_for_target(target_host)

    def __getitem__(self, target_host: str) -> TargetScopedFlagIds:
        return self.get_flag_ids_for_target(target_host)


class UnscopedFlagIds:
    """
    Flag IDs for all services, targets, and last N ticks provided by the game server. Allows traversing the flag IDs
    structure in a intuitive way.

    Example:
        Using `/` operator you can reduce the scope of the flag IDs to a specific service, target, or tick. The class
        hierarchy is as follows:

            `UnscopedFlagIds` -> `ServiceScopedFlagIds` -> `TargetScopedFlagIds` -> `TickScopedFlagIds` -> `Any`

        The following example demonstrates how to access flag IDs for a specific service, target, and tick:

        .. code-block:: python

            all_flag_ids: UnscopedFlagIds
            flag_ids: Any = all_flag_ids / "service_foo" / "10.10.13.37" / 0
    """

    def __init__(self, data: dict[str, dict[str, list[Any]]]):
        self._validate(data)
        self.services: set[ServiceScopedFlagIds] = {
            ServiceScopedFlagIds(service_name, targets_data) for service_name, targets_data in data.items()
        }

        self._service_name_map: dict[str, ServiceScopedFlagIds] = {
            service.service_name: service for service in self.services
        }

    def serialize(self) -> dict[str, dict[str, list[Any]]]:
        return {service.service_name: service.serialize() for service in self.services}

    def get_service_names(self) -> set[str]:
        """
        Returns a set of all service names for which flag ids are available.

        :return: Set of service names.
        :rtype: set[str]
        """
        return set(self._service_name_map.keys())

    def get_flag_ids_for_service(self, service_name: str) -> ServiceScopedFlagIds:
        """
        Returns the flag ids for a specific service and all its targets.

        :param service_name: Name of the service.
        :type service_name: str
        :return: Flag ids for the specified service.
        :rtype: ServiceScopedFlagIds
        :raises KeyError: If the service is not found.
        """
        if service_name in self._service_name_map:
            return self._service_name_map[service_name]
        else:
            raise KeyError(f"Service '{service_name}' not found")

    def walk(self) -> Iterator[TickScopedFlagIds]:
        for service in self.services:
            yield from service.walk()

    def copy(self) -> "UnscopedFlagIds":
        """
        Creates a deep copy of the flag IDs.

        :return: A deep copy of the flag IDs.
        :rtype: UnscopedFlagIds
        """
        return UnscopedFlagIds(self.serialize())

    @staticmethod
    def _validate(data: Any) -> None:
        if not isinstance(data, dict):
            raise ValueError("Flag IDs must be a dictionary.")

    def __truediv__(self, service_name: str) -> ServiceScopedFlagIds:
        return self.get_flag_ids_for_service(service_name)

    def __getitem__(self, service_name: str) -> ServiceScopedFlagIds:
        return self.get_flag_ids_for_service(service_name)

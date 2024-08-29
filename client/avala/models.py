import hashlib
from enum import Enum
from typing import NamedTuple, Any
from datetime import timedelta
from sqlalchemy import Column, String, Boolean, LargeBinary
from .database import Base, get_db


class Batching:
    def __init__(
        self,
        size: int | None = None,
        count: int | None = None,
        gap: float = 1.0,
    ):
        """
        Specifies the batching configuration for splitting a large number of attacks into smaller chunks, distributed over time.

        Batching provides a way of distributing the load over time with the goal of mitigating CPU, memory and network usage spikes.
        Setting up batching allows you to divide the list of targets into smaller, equally-sized and more manageable batches.

        Examples:
        ..
                # In case of 28 targets...
                # ...sizes of batches will be: [6, 6, 6, 6, 4]
                Batching(count=5, gap=2)

                # ...sizes of batches will be: [5, 5, 5, 5, 5, 3]
                Batching(size=5, gap=2)

        :param size: Specifies the size of each batch.
        :type size: int | None, optional
        :param count: Specifies the total number of equal-sized batches.
        :type count: int | None, optional
        :param gap: Specifies the time gap in seconds between processing two consecutive batches.
        :type gap: float, optional
        :raises ValueError: If both 'size' and 'count' are provided or if neither is provided.
        :raises ValueError: If 'size' is provided but is not a positive integer.
        :raises ValueError: If 'count' is provided but is not a positive integer.
        :raises ValueError: If 'gap' is not a positive number.
        """
        if size is None and count is None:
            raise ValueError("Either 'size' or 'count' must be set.")
        if size and count:
            raise ValueError("Only one of 'size' or 'count' can be set.")
        if size is not None and size <= 0:
            raise ValueError("'size' must be a positive integer.")
        if count is not None and count <= 0:
            raise ValueError("'count' must be a positive integer.")
        if gap <= 0:
            raise ValueError("'gap' must be a positive number.")

        self.size: int | None = size
        self.count: int | None = count
        self.gap = timedelta(seconds=gap)


class ExploitFuncMeta(NamedTuple):
    """
    NamedTuple representing metadata for an exploit function.

    Attributes:
        name (str):
            Name of the exploit function.
        module (str):
            Name of the module containing the exploit function.
        directory (str):
            Directory containing the exploit module.
        arg_count (int):
            Number of arguments expected by the exploit function.
    """

    name: str
    module: str
    directory: str
    arg_count: int


class TargetingStrategy(Enum):
    """
    Targeting strategy that can be used as an alternative to specifying a list of targets in the exploit configuration.

    When using TargetingStrategy.AUTO, the exploit function MUST take the `flag_ids` argument, and the targeted service
    MUST be defined in the `attacks.json` or `teams.json` provided by the game server. This is essential because
    automatic targeting relies on fetching the list of targets from these files.

    Attributes:
        AUTO:
            Selects the available targets based on `attack.json` or `teams.json` files provided by the game server.
            The exploit function MUST take the `flag_ids` argument, and the targeted service MUST be defined in the
            `attacks.json` or `teams.json` provided by the game server.
        NOP_TEAM:
            Selects the IP or hostname of the NOP team.
        OWN_TEAM:
            Selects the IP or hostname of your own team.
    """

    AUTO = "auto"
    NOP_TEAM = "nop_team"
    OWN_TEAM = "own_team"


class TickScope(Enum):
    """
    Enumeration representing the scope of ticks for which flag IDs are provided to the exploit function.

    Attributes:
        SINGLE:
            Specifies that the `flag_ids` object will contain only the flag IDs relevant to a single service, target, and tick.
            When using SINGLE, each flag ID that successfully returns a flag will be tracked and skipped in subsequent attempts,
            reducing the total number of attacks. This is the recommended approach.
        LAST_N:
            Specifies that the `flag_ids` object will contain a list of all flag IDs provided by the game server for the last N ticks.
    """

    SINGLE = "single"
    LAST_N = "last_n"


class FlagIdsHash(Base):
    """
    SQLAlchemy model representing a hash generated from the exploit alias, target, and the flag ID value for a specific tick.
    """

    __tablename__ = "hashes"

    value = Column(String, primary_key=True)


class StoredObject(Base):
    """
    SQLAlchemy model representing a stored blob in the database.
    """

    __tablename__ = "objects"

    key = Column(String, primary_key=True)
    value = Column(LargeBinary)


class PendingFlag(Base):
    """
    SQLAlchemy model representing a pending flag in the database.
    """

    __tablename__ = "pending_flags"

    value = Column(String, primary_key=True)
    target = Column(String)
    alias = Column(String)
    submitted = Column(Boolean, default=False)


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

    def __truediv__(self, index: int) -> Any:
        if 0 <= index < len(self.ticks):
            return self.ticks[index].flag_ids
        else:
            raise IndexError(f"Tick index '{index}' out of range")


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

    def get_targets(self) -> list[str]:
        """
        Returns a list of all targets for which attack data is available.

        :return: List of IP addresses or hostnames of the teams.
        :rtype: list[str]
        """
        return list(self.targets.keys())

    def serialize(self) -> dict[str, list[Any]]:
        return {target: ticks.serialize() for target, ticks in self.targets.items()}

    def __truediv__(self, target: str) -> TargetScopedAttackData:
        if target in self.targets:
            return self.targets[target]
        else:
            raise KeyError(f"Target '{target}' not found")


class UnscopedAttackData:
    """
    Attack data covering all services provided by the game server.
    """

    def __init__(self, data: dict[str, dict[str, list[Any]]]):
        self.services: dict[str, ServiceScopedAttackData] = {
            service: ServiceScopedAttackData(targets)
            for service, targets in data.items()
        }

    def get_services(self) -> list[str]:
        """
        Returns a list of all services for which attack data is available.

        :return: List of service names.
        :rtype: list[str]
        """
        return list(self.services.keys())

    def serialize(self) -> dict[
        str,
        dict[str, list[Any]],
    ]:
        return {service: data.serialize() for service, data in self.services.items()}

    def __truediv__(self, service: str) -> ServiceScopedAttackData:
        if service in self.services:
            return self.services[service]
        else:
            raise KeyError(f"Service '{service}' not found")


class ExploitConfig:
    def __init__(
        self,
        service: str,
        meta: ExploitFuncMeta,
        alias: str | None = None,
        targets: list[str] | TargetingStrategy = TargetingStrategy.AUTO,
        tick_scope: TickScope = TickScope.SINGLE,
        skip: list[str] | None = None,
        prepare: str | None = None,
        cleanup: str | None = None,
        command: str | None = None,
        env: dict[str, str] = {},
        delay: int = 0,
        batching: Batching | None = None,
        workers: int = 128,
        timeout: int = 15,
        is_draft: bool = False,
    ):
        self.service: str = service
        self.meta: ExploitFuncMeta = meta
        self.alias: str = alias or meta.module + "." + meta.name
        self.targets: list[str] | None = targets
        self.tick_scope: TickScope = tick_scope
        self.skip: list[str] | None = skip
        self.prepare: str | None = prepare
        self.cleanup: str | None = cleanup
        self.command: str | None = command
        self.env: dict[str, str] | None = env
        self.delay: timedelta = timedelta(seconds=delay or 0)
        self.batching: Batching | None = batching
        self.workers: int = workers
        self.timeout: int = timeout
        self.is_draft: bool = is_draft

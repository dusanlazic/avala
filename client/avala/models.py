import hashlib
from enum import Enum
from typing import NamedTuple
from datetime import timedelta
from sqlalchemy import Column, String
from .database import Base, get_db_context


class Batching:
    def __init__(
        self,
        size: int | None = None,
        count: int | None = None,
        gap: float = 0,
    ):
        if size is None and count is None:
            raise ValueError("Either 'size' or 'count' must be set.")
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
    name: str
    module: str
    directory: str
    arg_count: int


class TargetingStrategy(Enum):
    AUTO = "auto"
    NOP_TEAM = "nop_team"
    OWN_TEAM = "own_team"


class TickScope(Enum):
    SINGLE = "single"
    LAST_N = "last_n"


class FlagIdsHash(Base):
    __tablename__ = "hashes"

    value = Column(String, primary_key=True)


class TickScopedAttackData:
    def __init__(
        self,
        flag_ids: any,
    ):
        self.flag_ids: any = flag_ids

    @classmethod
    def hash_flag_ids(cls, alias: str, target: str, flag_ids: any) -> str:
        return hashlib.md5((alias + target + str(flag_ids)).encode()).hexdigest()

    def serialize(self) -> any:
        return self.flag_ids


class TargetScopedAttackData:
    def __init__(
        self,
        ticks: list[any],
    ):
        self.ticks: list[TickScopedAttackData] = [
            TickScopedAttackData(flag_ids) for flag_ids in ticks
        ]

    def remove_repeated(self, alias: str, target: str) -> "TargetScopedAttackData":
        with get_db_context() as db:
            hashes = [
                TickScopedAttackData.hash_flag_ids(alias, target, tick.flag_ids)
                for tick in self.ticks
            ]

            existing_hashes = [
                value
                for (value,) in db.query(FlagIdsHash.value)
                .filter(FlagIdsHash.value.in_(hashes))
                .all()
            ]

            self.ticks = [
                t for t, h in zip(self.ticks, hashes) if h not in existing_hashes
            ]

        return self

    def serialize(self) -> list[any]:
        return [tick.serialize() for tick in self.ticks]

    def __truediv__(self, index: int) -> any:
        if 0 <= index < len(self.ticks):
            return self.ticks[index].flag_ids
        else:
            raise IndexError(f"Tick index '{index}' out of range")


class ServiceScopedAttackData:
    def __init__(
        self,
        targets: dict[str, list[any]],
    ):
        self.targets: dict[str, TargetScopedAttackData] = {
            target: TargetScopedAttackData(ticks) for target, ticks in targets.items()
        }

    def get_targets(self) -> list[str]:
        return list(self.targets.keys())

    def serialize(self) -> dict[str, list[any]]:
        return {target: ticks.serialize() for target, ticks in self.targets.items()}

    def __truediv__(self, target: str) -> TargetScopedAttackData:
        if target in self.targets:
            return self.targets[target]
        else:
            raise KeyError(f"Target '{target}' not found")


class UnscopedAttackData:
    def __init__(self, data):
        self.services: dict[str, ServiceScopedAttackData] = {
            service: ServiceScopedAttackData(targets)
            for service, targets in data.items()
        }

    def serialize(self) -> dict[
        str,
        dict[str, list[any]],
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
        timeout: int = 0,
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
        self.timeout: int = timeout

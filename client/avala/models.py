from enum import Enum
from typing import NamedTuple
from datetime import timedelta


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


class ExploitConfig:
    def __init__(
        self,
        service: str,
        meta: ExploitFuncMeta,
        alias: str | None = None,
        targets: list[str] | TargetingStrategy = TargetingStrategy.AUTO,
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
        self.skip: list[str] | None = skip
        self.prepare: str | None = prepare
        self.cleanup: str | None = cleanup
        self.command: str | None = command
        self.env: dict[str, str] | None = env
        self.delay: timedelta = timedelta(seconds=delay or 0)
        self.batching: Batching | None = batching
        self.timeout: int = timeout

from enum import Enum
from typing import NamedTuple
from datetime import timedelta


class BatchBySize:
    def __init__(self, size: int, gap: int):
        self.size = size
        self.gap = timedelta(seconds=gap)


class BatchByCount:
    def __init__(self, count: int, gap: int):
        self.count = count
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
        batching: BatchBySize | BatchByCount | None = None,
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
        self.batching: BatchBySize | BatchByCount | None = batching
        self.timeout: int = timeout

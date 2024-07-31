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


class FunctionMeta(NamedTuple):
    name: str
    module: str
    directory: str


class ExploitConfig:
    def __init__(
        self,
        service: str,
        meta: FunctionMeta,
        alias: str | None = None,
        targets: list[str] | None = None,
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
        self.meta: FunctionMeta = meta
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

        self.automatic_targets: bool = not bool(targets)

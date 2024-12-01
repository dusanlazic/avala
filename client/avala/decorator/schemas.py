from datetime import timedelta

from pydantic import BaseModel, PositiveInt, model_validator
from typing_extensions import Self

from .enums import TargetingStrategy, TickScope


class Batching(BaseModel):
    """
    Specifies the batching configuration for splitting a large number of attacks into smaller chunks, distributed over time.

    Batching provides a way of distributing the load over time with the goal of mitigating CPU, memory, and network usage spikes.
    Setting up batching allows you to divide the list of targets into smaller, equally-sized, and more manageable batches.

    Examples:
        In case of **28** targets, the sizes of batches will be: **6, 6, 6, 6, 4**.

        .. code-block:: python

            Batching(count=5, interval=2)

        In case of **28** targets, the sizes of batches will be: **5, 5, 5, 5, 5, 3**.

        .. code-block:: python

            Batching(size=5, interval=2)

    :param size: Specifies the size of each batch.
    :type size: int | None
    :param count: Specifies the total number of equal-sized batches.
    :type count: int | None
    :param interval: Specifies the time gap in seconds between processing two consecutive batches.
    :type interval: int | float | timedelta
    """

    size: PositiveInt | None = None
    count: PositiveInt | None = None
    interval: timedelta = timedelta(seconds=1)

    @model_validator(mode="after")
    def check_either_size_or_count_set(self) -> Self:
        if self.size is None and self.count is None:
            raise ValueError("Either 'size' or 'count' must be set.")
        if self.size and self.count:
            raise ValueError("Only one of 'size' or 'count' can be set.")
        return self


class ExploitFuncMeta(BaseModel):
    """
    Represents metadata for an exploit function.

    :param name: Name of the exploit function.
    :type name: str
    :param module: Name of the module containing the exploit function.
    :type module: str
    :param directory: Directory containing the exploit module.
    :type directory: str
    :param arg_count: Number of arguments expected by the exploit function.
    :type arg_count: int
    """

    name: str
    module: str
    directory: str
    arg_count: int


class ExploitConfig:
    def __init__(
        self,
        service: str,
        meta: ExploitFuncMeta,
        draft: bool = False,
        alias: str | None = None,
        target_hosts: list[str] | None = None,
        target_strategy: TargetingStrategy | None = None,
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
    ):
        self.service: str = service
        self.is_draft: bool = draft
        self.meta: ExploitFuncMeta = meta
        self.alias: str = alias or meta.module + "." + meta.name
        self.target_hosts: list[str] | None = target_hosts
        self.target_strategy: TargetingStrategy | None = target_strategy
        self.tick_scope: TickScope = tick_scope
        self.skip: list[str] | None = skip
        self.prepare: str | None = prepare
        self.cleanup: str | None = cleanup
        self.command: str | None = command
        self.env: dict[str, str] = env
        self.delay: timedelta = (
            timedelta(seconds=delay or 0) if not draft else timedelta(seconds=0)
        )
        self.batching: Batching | None = batching if not draft else None
        self.workers: int = workers
        self.timeout: int = timeout

from datetime import timedelta

from pydantic import BaseModel, PositiveFloat, PositiveInt, field_validator, model_validator
from typing_extensions import Self


class Batching(BaseModel):
    """
    Specifies the batching configuration for splitting a large number of attacks into smaller chunks, distributed over
    time.

    Batching provides a way of distributing the load over time with the goal of mitigating CPU, memory, and network
    usage spikes. Setting up batching allows you to divide the list of targets into smaller, equally-sized, and more
    manageable batches.

    Examples:
        In case of **28** targets, the sizes of batches will be: **6, 6, 6, 6, 4**.

        .. code-block:: python

            Batching(count=5, interval=2)

        In case of **28** targets, the sizes of batches will be: **5, 5, 5, 5, 5, 3**.

        .. code-block:: python

            Batching(size=5, interval=2)

    :param size: Size of each batch.
    :type size: int | None
    :param count: Total number of equal-sized batches.
    :type count: int | None
    :param interval: Interval in seconds between processing two consecutive batches.
    :type interval: int | float | timedelta
    """

    size: PositiveInt | None = None
    count: PositiveInt | None = None
    interval: PositiveInt | PositiveFloat | timedelta = timedelta(seconds=1)

    @field_validator("interval", mode="before")
    @classmethod
    def convert_interval(cls, v):
        if isinstance(v, (int, float)):
            return timedelta(seconds=v)
        return v

    @model_validator(mode="after")
    def check_either_size_or_count_set(self) -> Self:
        if self.size is None and self.count is None:
            raise ValueError("Either 'size' or 'count' must be set.")
        if self.size and self.count:
            raise ValueError("Only one of 'size' or 'count' can be set.")
        return self

import os
from addict import Dict
from functools import wraps
from collections import namedtuple

class BatchBySize(namedtuple("BatchBySize", "size gap")):
    def to_dict(self):
        return Dict(self._asdict())


class BatchByCount(namedtuple("BatchByCount", "count gap")):
    def to_dict(self):
        return Dict(self._asdict())


def exploit(
    service: str,
    alias: str | None = None,
    targets: list[str] | None = None,
    skip: list[str] | None = None,
    prepare: str | None = None,
    cleanup: str | None = None,
    env: dict[str, str] = None,
    delay: int = 0,
    batching: BatchBySize | BatchByCount | None = None,
    timeout: int = 0,
):
    def decorator_exploit(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.exploit_config = Dict(
            {
                "alias": alias,
                "targets": targets,
                "skip": skip,
                "service": service,
                "prepare": prepare,
                "cleanup": cleanup,
                "env": env,
                "delay": delay,
                "batching": batching.to_dict() if batching else None, # TODO: Tidy up
                "timeout": timeout,
                "meta": {
                    "name": func.__name__,
                    "module": func.__module__,
                    "directory": os.path.dirname(func.__code__.co_filename),
                },
            }
        )

        return wrapper

    return decorator_exploit

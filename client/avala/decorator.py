import os
from functools import wraps
from .models import BatchBySize, BatchByCount, FunctionMeta, ExploitConfig


def exploit(
    service: str,
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
    def decorator_exploit(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.exploit_config = ExploitConfig(
            service=service,
            alias=alias,
            targets=targets,
            skip=skip,
            prepare=prepare,
            cleanup=cleanup,
            command=command,
            env=env,
            delay=delay,
            batching=batching,
            timeout=timeout,
            meta=FunctionMeta(
                name=func.__name__,
                module=func.__module__,
                directory=os.path.dirname(func.__code__.co_filename),
            ),
        )

        return wrapper

    return decorator_exploit

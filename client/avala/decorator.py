import os
from functools import wraps
from .models import (
    Batching,
    ExploitFuncMeta,
    ExploitConfig,
    TargetingStrategy,
    TickScope,
)


def exploit(
    service: str,
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
    def decorator_exploit(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.is_draft = False
        wrapper.exploit_config = ExploitConfig(
            service=service,
            alias=alias,
            targets=targets,
            tick_scope=tick_scope,
            skip=skip,
            prepare=prepare,
            cleanup=cleanup,
            command=command,
            env=env,
            delay=delay,
            batching=batching,
            timeout=timeout,
            meta=ExploitFuncMeta(
                name=func.__name__,
                module=func.__module__,
                directory=os.path.dirname(func.__code__.co_filename),
                arg_count=func.__code__.co_argcount,
            ),
        )

        return wrapper

    return decorator_exploit


def draft(
    service: str,
    targets: list[str] | TargetingStrategy,
    alias: str | None = None,
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
    def decorator_exploit(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.is_draft = True
        wrapper.exploit_config = ExploitConfig(
            service=service,
            alias=alias,
            targets=targets,
            tick_scope=tick_scope,
            skip=skip,
            prepare=prepare,
            cleanup=cleanup,
            command=command,
            env=env,
            delay=0,
            timeout=timeout,
            meta=ExploitFuncMeta(
                name=func.__name__,
                module=func.__module__,
                directory=os.path.dirname(func.__code__.co_filename),
                arg_count=func.__code__.co_argcount,
            ),
        )

        return wrapper

    return decorator_exploit

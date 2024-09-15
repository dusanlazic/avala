import os
from functools import wraps

from .models import (
    Batching,
    ExploitConfig,
    ExploitFuncMeta,
    TargetingStrategy,
    TickScope,
)


def exploit(
    service: str,
    draft: bool = False,
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
    timeout: int = 15,
    workers: int = 128,
):
    """
    A decorator to mark a function as an exploit.

    :param service: Name of the service attacked by the exploit. To see all services, you can use `get_services()` method of `Avala` instance.
    :type service: str
    :param draft: Whether the exploit is a draft or not. Draft exploits are not executed when running client by calling `run()` method, but are executed by calling `workshop()`. Enabling this options ignores `delay` and `batching` options. Defaults to False.
    :type draft: bool
    :param targets: IP addresses or hostnames of the targeted teams, or a targeting strategy (`AUTO`, `OWN_TEAM`, `NOP_TEAM`).
    Manually specify targets or use one of targeting strategies: `TargetingStrategy.AUTO` to target all currently available teams if your exploit is accepting `flag_ids` parameter; `TargetingStrategy.OWN_TEAM` to target your own team; `TargetingStrategy.NOP_TEAM` to target the NOP team.
    :type targets: list[str] | TargetingStrategy
    :param alias: Alias used for exploit identification, analytics and as a key for tracking repeated flag IDs.
    If not provided, it will be set to `<module_name>.<function_name>`.
    :type alias: str | None, optional
    :param tick_scope: Scope of the `flag_ids` dictionary, defaults to TickScope.SINGLE.
    Read more about tick scopes in :class:`avala.models.TickScope`.
    :type tick_scope: TickScope, optional
    :param skip: IP addresses or hostnames to skip while attacking. Defaults to the addresses belonging to the NOP team and own team, **unless the targeting strategy is set to `NOP_TEAM` or `OWN_TEAM`**.
    :type skip: list[str] | None, optional
    :param prepare: Optional shell command to run before starting the first attack, defaults to None. Useful for setting up the environment, files, etc.
    :type prepare: str | None, optional
    :param cleanup: Optional shell command to run after completing the last attack, defaults to None. Useful for cleaning up any changes or artifacts created during the attacks.
    :type cleanup: str | None, optional
    :param command: Command for running a non-Python exploit. Must be a string with placeholders for the target IP (`{target}`) address and path to the exported flag IDs dictionary (`{flag_ids_path}`).
    Example: `./rust_exploit {target} {flag_ids_path}`. Defaults to None.
    :type command: str | None, optional
    :param env: Environment variables to be passed into the exploit's execution environment. Any passed environment variables will be merged with the current environment variables. Defaults to an empty dictionary.
    :type env: dict[str, str], optional
    :param delay: Delay in seconds to wait before starting the first attack, defaults to 0. This is helpful when running multiple exploits to prevent them from running at the same time, which could lead to excessive CPU, memory or network usage.
    Note: Delay is **ignored in draft exploits** and is listed for easier switching between draft and non-draft exploits.
    :type delay: int, optional
    :param timeout: Timeout in seconds after which the exploit will be terminated if it's stuck or takes too long to complete, defaults to 15. Note that the timeout is applied to the exploit execution itself and not each individual attack: timeout is applied on batches of exploits, and your exploit will likely timeout if the number of `workers` is too low.
    :type timeout: int, optional
    :param batching: Batching configuration, defaults to None meaning no batching. Provides a way of distributing the load over time with the goal of mitigating CPU, memory and network usage spikes.
    Read more about batching in :class:`avala.models.Batching`. Note: Batching is **ignored in draft exploits** and is listed for easier switching between draft and non-draft exploits.
    :type batching: Batching | None, optional
    :param workers: Number of concurrent workers **per exploit** to be used for executing the attacks, defaults to 128.
    :type workers: int, optional
    """

    def decorator_exploit(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.exploit_config = ExploitConfig(
            service=service,
            draft=draft,
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
            workers=workers,
            meta=ExploitFuncMeta(
                name=func.__name__,
                module=func.__module__,
                directory=os.path.dirname(func.__code__.co_filename),
                arg_count=func.__code__.co_argcount,
            ),
        )

        return wrapper

    return decorator_exploit

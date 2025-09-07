from datetime import timedelta
from functools import wraps
from typing import Iterable

from ..exploit import Exploit
from .enums import FlagIdScope, TargetingStrategy
from .schemas import Batching


def exploit(
    service: str,
    draft: bool = False,
    alias: str | None = None,
    targets: Iterable[str] | TargetingStrategy = TargetingStrategy.AUTO,
    flag_id_scope: FlagIdScope = FlagIdScope.SINGLE_TICK,
    skip: Iterable[str] | None = None,
    include: Iterable[str] | None = None,
    delay: int | float | timedelta = timedelta(seconds=0),
    batching: Batching = Batching(count=1),
    timeout: int | float | timedelta = timedelta(seconds=15),
):
    """
    Decorator for defining and configuring an exploit.

    :param service: Name of the service attacked by the exploit. To see the names of available services, run `avl services`.
    :type service: str
    :param draft: Exclude the exploit when running Avala in production mode. Useful for testing and debugging exploits when running manually. Defaults to False.
    :type draft: bool
    :param alias: Alias used for exploit identification, logging and as a key for tracking repeated flag IDs.
    :type alias: str | None
    :param targets: IP addresses or hostnames of the targeted teams, or a targeting strategy. Defaults to `TargetingStrategy.AUTO`.
    :type targets: Iterable[str] | TargetingStrategy
    :param flag_id_scope: Tick scope of the flag IDs provided to the exploit function, defaults to
    FlagIdScope.SINGLE_TICK.
    :type flag_id_scope: FlagIdScope
    :param skip: IP addresses or hostnames to skip when attacking. Hosts of the NOP team and own team are skipped by
    default.
    :type skip: Iterable[str] | None
    :param include: Additional IP addresses or hostnames to include when attacking. Can be used to include hosts that
    are skipped by default (NOP team and own team).
    :type include: Iterable[str] | None
    :param delay: Delay in seconds to wait before starting the first attack, defaults to 0. Useful when running
    multiple exploits and need a way to prevent them from running at the same time, which could lead to excessive CPU, memory or network usage.
    :type delay: int | float | timedelta, optional
    :param batching: Batching configuration, defaults to `Batching(count=1)` meaning no batching. Provides a way of distributing the load over time with the goal of mitigating CPU, memory and network usage spikes.
    :type batching: Batching | None, optional
    :param timeout: Timeout in seconds after which the exploit will be terminated if it hangs or takes too long to complete, defaults to 15.
    :type timeout: int, optional
    """  # noqa: E501

    def exploit_decorator(func):
        """
        Creates a runnable `Exploit` object based on the user-defined configuration and associates it with the decorated
        function. Makes the decorated function discoverable by Avala and allows it to setup and run the exploit
        afterwards.
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.exploit = Exploit(
            service=service,
            is_draft=draft,
            alias=alias or f"{func.__module__}.{func.__name__}",
            targets_skip=set(skip) if skip else set(),
            targets_include=set(include) if include else set(),
            targets_explicit=set(targets) if isinstance(targets, Iterable) else set(),
            targets_strategy=targets if isinstance(targets, TargetingStrategy) else None,
            flag_id_scope=flag_id_scope,
            delay=timedelta(seconds=delay) if isinstance(delay, (int, float)) else delay,
            batching=batching,
            timeout=timedelta(seconds=timeout) if isinstance(timeout, (int, float)) else timeout,
            func=func,
        )

        return wrapper

    return exploit_decorator

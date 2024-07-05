import re
import os
import sys
import argparse
import concurrent.futures
from typing import Callable, Any
from importlib import import_module
from shared.logs import logger

FLAG_REGEX = "ENO[A-Za-z0-9+\/=]{48}"  # TODO: Propagate from server to here


def main(args):
    exploit = import_exploit_func(args.module)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(exploit, target) for target in args.targets]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            flags = match_flags(FLAG_REGEX, result)
            # TODO: Enqueue flags
            logger.success(flags)


def import_exploit_func(module) -> Callable[[str], Any]:
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.append(cwd)

    module = import_module(module)
    exploit_func = getattr(module, "exploit", None)

    return exploit_func


def match_flags(pattern: str, text: str) -> bool:
    matches = re.findall(pattern, text)
    return matches if matches else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run attacks concurrently against provided teams using provided exploit."
    )
    parser.add_argument(
        "targets",
        type=str,
        nargs="+",
        help="IP addresses of targeted teams.",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Alias of the exploit for its identification.",
    )
    parser.add_argument(
        "--module",
        type=str,
        required=True,
        help="Name of the Python module of the exploit (must contain 'exploit' function).",
    )
    parser.add_argument(
        "--timeout",
        default=10,
        type=str,
        required=True,
        help="Optional timeout for a single attack in seconds.",
    )

    args = parser.parse_args()
    main(args)

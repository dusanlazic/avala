import re
import os
import sys
import shlex
import argparse
import subprocess
import concurrent.futures
from typing import Callable, Any
from importlib import import_module
from shared.logs import logger
from client.api import client


def main(args):
    client.import_settings()

    if args.prepare:
        if isinstance(args.prepare, str):
            subprocess.run(shlex.split(args.prepare), text=True)
        elif prepare := import_func(args.module, "prepare"):
            prepare()

    exploit = import_func(args.module, "exploit")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(exploit, target): target
            for target in args.targets
            if target not in [client.game.team_ip, client.game.nop_team_ip]
        }

        for future in concurrent.futures.as_completed(futures):
            target = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.error(
                    f"An error has occured while attacking <bold>%s</> via <bold>%s</>: %s"
                    % (target, args.name, e),
                )
                continue

            flags = match_flags(client.game.flag_format, result)
            if not flags:
                logger.warning(
                    "No flags retrieved from attacking <bold>%s</> via <bold>%s</>."
                    % (target, args.name)
                )
                continue

            client.enqueue(flags, args.name, target)

    if args.cleanup:
        if isinstance(args.cleanup, str):
            subprocess.run(shlex.split(args.cleanup), text=True)
        elif cleanup := import_func(args.module, "cleanup"):
            cleanup()


def import_func(module, name) -> Callable[[str], Any]:
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.append(cwd)

    module = import_module(module)
    return getattr(module, name, None)


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
        help="IP addresses or hostnames of targeted teams.",
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
        type=int,
        required=True,
        help="Optional timeout for a single attack in seconds.",
    )
    parser.add_argument(
        "--prepare",
        nargs="?",
        const=True,
        default=None,
        help="Run prepare Python function if exists, or run provided shell command before running the attack.",
    )
    parser.add_argument(
        "--cleanup",
        nargs="?",
        const=True,
        default=None,
        help="Run cleanup Python function if exists, or run provided shell command after running the attack.",
    )

    args = parser.parse_args()
    main(args)

import re
import os
import sys
import json
import shlex
import argparse
import subprocess
import concurrent.futures
from typing import Callable
from importlib import import_module
from avala.shared.logs import logger
from avala.shared.util import colorize
from avala.api import APIClient
from avala.models import ServiceScopedAttackData, TickScope


def main(args):
    client = APIClient()
    client.import_settings()

    execute_attack = None

    try:
        execute_attack = import_func(args.func_name, args.module, args.directory)
    except Exception as e:
        logger.error(
            "An error has occured while importing exploit function <bold>%s</> from <bold>%s.py</>: %s"
            % (args.func_name, args.module, e)
        )

    if not execute_attack:
        exit(1)

    if args.prepare:
        subprocess.run(shlex.split(args.prepare), text=True)

    service_attack_data = (
        read_flag_ids(args.attack_data_file) if args.attack_data_file else None
    )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        if service_attack_data:
            if args.tick_scope == TickScope.SINGLE.value:
                futures = {
                    executor.submit(
                        execute_attack,
                        target,
                        tick,
                    ): target
                    for target in args.targets
                    for tick in (service_attack_data / target).serialize()
                    if target not in [client.game.team_ip, client.game.nop_team_ip]
                }
            elif args.tick_scope == TickScope.LAST_N.value:
                futures = {
                    executor.submit(
                        execute_attack,
                        target,
                        (service_attack_data / target).serialize(),
                    ): target
                    for target in args.targets
                    if target not in [client.game.team_ip, client.game.nop_team_ip]
                }
        else:
            futures = {
                executor.submit(execute_attack, target): target
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
                    % (colorize(target), colorize(args.alias), e),
                )
                continue

            flags = match_flags(client.game.flag_format, result)
            if not flags:
                logger.warning(
                    "No flags retrieved from attacking <bold>%s</> via <bold>%s</>."
                    % (colorize(target), colorize(args.alias))
                )
                continue

            client.enqueue(flags, args.alias, target)

    if args.cleanup:
        subprocess.run(shlex.split(args.cleanup), text=True)


def import_func(name, module, directory=os.getcwd()) -> Callable:
    if directory not in sys.path:
        sys.path.append(directory)

    module = import_module(module)
    return getattr(module, name, None)


def match_flags(pattern: str, text: str) -> bool:
    matches = re.findall(pattern, text)
    return matches if matches else None


def read_flag_ids(filepath: str) -> ServiceScopedAttackData | None:
    try:
        with open(filepath) as file:
            return ServiceScopedAttackData(json.load(file))
    except FileNotFoundError:
        logger.error("Flag IDs file <bold>%s</> not found." % filepath)
        return
    except PermissionError:
        logger.error("Flag IDs file <bold>%s</> is not accessible." % filepath)
        return
    except json.JSONDecodeError:
        logger.error("Flag IDs file <bold>%s</> is not a valid JSON." % filepath)
        return
    except Exception as e:
        logger.error(
            "An error has occured while reading flag IDs file: %s" % e,
        )
        return


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
        "--alias",
        type=str,
        required=True,
        help="Alias of the exploit for its identification.",
    )
    parser.add_argument(
        "--func-name",
        type=str,
        required=True,
        help="Name of the exploit function to be imported and executed.",
    )
    parser.add_argument(
        "--module",
        type=str,
        required=True,
        help="Name of the Python module of the exploit.",
    )
    parser.add_argument(
        "--directory",
        type=str,
        required=True,
        help="Directory of the Python module of the exploit.",
    )
    parser.add_argument(
        "--timeout",
        default=10,
        type=int,
        help="Optional timeout for a single attack in seconds.",
    )
    parser.add_argument(
        "--attack-data-file",
        type=str,
        help="Path to a file containing attack data of all targets of the specified service.",
    )
    parser.add_argument(
        "--tick-scope",
        type=str,
        default="single",
        choices=["single", "last_n"],
        help="Tick scope of the flag_ids object to be used for the exploit.",
    )
    parser.add_argument(
        "--prepare",
        nargs="?",
        const=True,
        help="Run provided shell command before running the first attack.",
    )
    parser.add_argument(
        "--cleanup",
        nargs="?",
        const=True,
        help="Run provided shell command after running the last attacks.",
    )

    args = parser.parse_args()
    main(args)

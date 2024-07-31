import os
import re
import json
import shlex
import argparse
import tempfile
import subprocess
import concurrent.futures
from avala.shared.logs import logger
from avala.shared.util import colorize
from avala.api import APIClient


TARGET_PLACEHOLDER = "{target}"
FLAG_IDS_PATH_PLACEHOLDER = "{flag_ids_path}"


def main(args):
    client = APIClient()
    client.import_settings()

    if args.prepare:
        subprocess.run(shlex.split(args.prepare), text=True)

    flag_ids = read_flag_ids(args.flag_ids_file) if args.flag_ids_file else None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # TODO: Handle KeyError
        if flag_ids:
            futures = {
                executor.submit(
                    execute_attack, args.command, target, flag_ids[target]
                ): target
                for target in args.targets
                if target not in [client.game.team_ip, client.game.nop_team_ip]
            }
        else:
            futures = {
                executor.submit(execute_attack, args.command, target): target
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


def execute_attack(command, target, flag_ids=None):
    command_args = [
        target if arg == TARGET_PLACEHOLDER else arg for arg in shlex.split(command)
    ]

    if flag_ids is not None:
        flag_ids_path = export_flag_ids(flag_ids)
        if FLAG_IDS_PATH_PLACEHOLDER in command_args:
            command_args = [
                flag_ids_path if arg == FLAG_IDS_PATH_PLACEHOLDER else arg
                for arg in command_args
            ]

    result = subprocess.run(command_args, text=True, capture_output=True)
    result.check_returncode()

    try:
        if flag_ids:
            os.unlink(flag_ids_path)
    except FileNotFoundError:
        pass

    return result.stdout


def match_flags(pattern: str, text: str) -> bool:
    matches = re.findall(pattern, text)
    return matches if matches else None


def read_flag_ids(filepath: str):
    try:
        with open(filepath) as file:
            return json.load(file)
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


def export_flag_ids(flag_ids):
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
        json.dump(flag_ids, file)
        return file.name


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
        "--command",
        type=str,
        required=True,
        help="Command that runs the exploit (must contain '[ip]' placeholder).",
    )
    parser.add_argument(
        "--timeout",
        default=10,
        type=int,
        required=True,
        help="Optional timeout for a single attack in seconds.",
    )
    parser.add_argument(
        "--flag-ids-file",
        type=str,
        help="Path to a file containing flag IDs of the specified service.",
    )
    parser.add_argument(
        "--prepare",
        type=str,
        help="Shell command to run before running the attack.",
    )
    parser.add_argument(
        "--cleanup",
        type=str,
        help="Shell command to run after running the attack.",
    )

    args = parser.parse_args()
    main(args)

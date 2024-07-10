import re
import shlex
import argparse
import subprocess
import concurrent.futures
from shared.logs import logger
from client.api import client


def main(args):
    client.import_settings()

    if args.prepare:
        subprocess.run(shlex.split(args.prepare), text=True)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(exploit, args.command, target): target
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
        subprocess.run(shlex.split(args.cleanup), text=True)


def exploit(command, target):
    command_args = [target if arg == "[ip]" else arg for arg in shlex.split(command)]
    result = subprocess.run(command_args, text=True, capture_output=True)
    result.check_returncode()
    return result.stdout


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

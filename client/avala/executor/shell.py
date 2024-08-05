import os
import re
import json
import shlex
import argparse
import tempfile
import subprocess
import concurrent.futures
from sqlalchemy.dialects.sqlite import insert
from avala.shared.logs import logger
from avala.shared.util import colorize
from avala.api import APIClient
from avala.models import (
    ServiceScopedAttackData,
    TickScopedAttackData,
    TickScope,
    FlagIdsHash,
)
from avala.database import get_db


TARGET_PLACEHOLDER = "{target}"
FLAG_IDS_PATH_PLACEHOLDER = "{flag_ids_path}"


def main(args):
    client = APIClient()
    client.import_settings()

    if args.prepare:
        subprocess.run(shlex.split(args.prepare), text=True)

    service_attack_data = (
        read_flag_ids(args.attack_data_file) if args.attack_data_file else None
    )

    with concurrent.futures.ThreadPoolExecutor() as executor, get_db() as db:
        if service_attack_data:
            if args.tick_scope == TickScope.SINGLE.value:
                futures = {
                    executor.submit(
                        execute_attack,
                        args.command,
                        target,
                        flag_ids,
                    ): (target, flag_ids)
                    for target in args.targets
                    for flag_ids in (service_attack_data / target)
                    .remove_repeated(args.alias, target, is_draft=args.draft)
                    .serialize()
                    if target not in [client.game.team_ip, client.game.nop_team_ip]
                }
            elif args.tick_scope == TickScope.LAST_N.value:
                futures = {
                    executor.submit(
                        execute_attack,
                        args.command,
                        target,
                        (service_attack_data / target)
                        .remove_repeated(args.alias, target, is_draft=args.draft)
                        .serialize(),
                    ): (target, None)
                    for target in args.targets
                    if target not in [client.game.team_ip, client.game.nop_team_ip]
                }
        else:
            futures = {
                executor.submit(execute_attack, args.command, target): target
                for target in args.targets
                if target not in [client.game.team_ip, client.game.nop_team_ip]
            }

        used_flag_id_hashes: list[str] = []

        for future in concurrent.futures.as_completed(futures):
            target, flag_ids = futures[future]
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

            if flag_ids:
                used_flag_id_hashes.append(
                    TickScopedAttackData.hash_flag_ids(args.alias, target, flag_ids)
                )

        if used_flag_id_hashes:
            db.execute(
                insert(FlagIdsHash)
                .values([{"value": value} for value in used_flag_id_hashes])
                .on_conflict_do_nothing(index_elements=["value"])
            )

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

    logger.debug(
        "🔎 <bold>%s</>-><bold>%s</> (stdout):\n%s"
        % (colorize(args.alias), colorize(target), result.stdout)
    )

    if result.stderr:
        logger.debug(
            "🔎 <bold>%s</>-><bold>%s</> (stderr):\n%s"
            % (colorize(args.alias), colorize(target), result.stderr)
        )

    return result.stdout


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
        type=str,
        help="Shell command to run before running the attack.",
    )
    parser.add_argument(
        "--cleanup",
        type=str,
        help="Shell command to run after running the attack.",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        default=False,
        help="Do not skip attacks that use already used flag ids.",
    )

    args = parser.parse_args()
    main(args)

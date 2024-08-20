import os
import re
import sys
import json
import shlex
import argparse
import tempfile
import subprocess
import concurrent.futures
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from avala.shared.logs import logger
from avala.shared.util import colorize
from avala.api import APIClient
from avala.models import (
    ServiceScopedAttackData,
    TickScopedAttackData,
    TickScope,
    FlagIdsHash,
    PendingFlag,
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

    used_flag_id_hashes: list[dict] = []
    pending_flags: list[dict] = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor, get_db() as db:
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
                    for flag_ids in get_flag_ids(service_attack_data, target, db)
                }
            elif args.tick_scope == TickScope.LAST_N.value:
                futures = {
                    executor.submit(
                        execute_attack,
                        args.command,
                        target,
                        get_flag_ids(service_attack_data, target, db),
                    ): (target, None)
                    for target in args.targets
                }
        else:
            futures = {
                executor.submit(execute_attack, args.command, target): target
                for target in args.targets
            }

        for future in concurrent.futures.as_completed(futures):
            target, flag_ids = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.error(
                    "An error has occurred while attacking <b>{target}</> via <b>{alias}</>: {error}",
                    target=colorize(target),
                    alias=colorize(args.alias),
                    error=e,
                )
                continue

            flags = match_flags(client.game.flag_format, result)
            if not flags:
                logger.warning(
                    "No flags retrieved from attacking <b>{target}</> via <b>{alias}</>.",
                    target=colorize(target),
                    alias=colorize(args.alias),
                )
                continue

            try:
                client.enqueue(flags, args.alias, target)
            except Exception as e:
                logger.error(
                    "Failed to enqueue flags from <b>{target}</> via <b>{alias}</>: {error}",
                    target=target,
                    alias=args.alias,
                    error=e,
                )

                pending_flags.extend(
                    [
                        {
                            "value": value,
                            "target": target,
                            "alias": args.alias,
                        }
                        for value in flags
                    ]
                )

            if flag_ids:
                used_flag_id_hashes.append(
                    {
                        "value": TickScopedAttackData.hash_flag_ids(
                            args.alias, target, flag_ids
                        )
                    }
                )

        if used_flag_id_hashes:
            db.execute(
                insert(FlagIdsHash)
                .values(used_flag_id_hashes)
                .on_conflict_do_nothing(index_elements=["value"])
            )

        if pending_flags:
            db.execute(
                insert(PendingFlag)
                .values(pending_flags)
                .on_conflict_do_nothing(index_elements=["value"])
            )
            logger.warning(
                "<b>{count}</> more flags obtained via <b>{alias}</> are stored into the local flag store.",
                count=len(pending_flags),
                alias=colorize(args.alias),
            )

    if args.cleanup:
        subprocess.run(shlex.split(args.cleanup), text=True)


def execute_attack(command, target, flag_ids=None) -> str:
    """
    Executes the attack by running the provided command within a subprocess.
    Returns the command's output to the standard output.
    """
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

    try:
        result = subprocess.run(
            command_args, text=True, capture_output=True, timeout=args.timeout
        )
    except subprocess.TimeoutExpired:
        sys.exit(2)
    finally:
        try:
            if flag_ids:
                os.unlink(flag_ids_path)
        except FileNotFoundError:
            pass

    if args.draft:
        logger.debug(
            "🔎 <b>{alias}</>-><b>{target}</> (stdout):\n{output}",
            alias=colorize(args.alias),
            target=colorize(target),
            output=result.stdout,
        )

        if result.stderr:
            logger.debug(
                "🔎 <b>{alias}</>-><b>{target}</> (stderr):\n{output}",
                alias=colorize(args.alias),
                target=colorize(target),
                output=result.stderr,
            )

    return result.stdout


def match_flags(pattern: str, output: str) -> list[str]:
    return re.findall(pattern, output)


def read_flag_ids(filepath: str) -> ServiceScopedAttackData | None:
    try:
        with open(filepath) as file:
            return ServiceScopedAttackData(json.load(file))
    except FileNotFoundError:
        logger.error("Flag IDs file <b>{file}</> not found.", file=filepath)
        return
    except PermissionError:
        logger.error("Flag IDs file <b>{file}</> is not accessible.", file=filepath)
        return
    except json.JSONDecodeError:
        logger.error("Flag IDs file <b>{file}</> is not a valid JSON.", file=filepath)
        return
    except Exception as e:
        logger.error(
            "An error has occurred while reading flag IDs file: {error}",
            error=e,
        )
        return


def export_flag_ids(flag_ids):
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
        json.dump(flag_ids, file)
        return file.name


def get_flag_ids(
    service_attack_data: ServiceScopedAttackData,
    target: str,
    db: Session,
) -> list:
    try:
        flag_ids = service_attack_data / target
    except KeyError:
        logger.error(
            "Target <b>{target}</> not found for exploit <b>{alias}</>.",
            target=colorize(target),
            alias=colorize(args.alias),
        )
        return []

    if args.draft:
        return flag_ids.serialize()

    hashes = [
        TickScopedAttackData.hash_flag_ids(args.alias, target, tick.flag_ids)
        for tick in flag_ids.ticks
    ]

    existing_hashes = [
        value
        for (value,) in db.query(FlagIdsHash.value)
        .filter(FlagIdsHash.value.in_(hashes))
        .all()
    ]

    flag_ids.ticks = [
        t for t, h in zip(flag_ids.ticks, hashes) if h not in existing_hashes
    ]

    return flag_ids.serialize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run attacks concurrently against provided teams using provided exploit."
    )
    parser.add_argument(
        "targets",
        type=str,
        nargs="+",
        help="IP addresses or hostnames of the targeted teams.",
    )
    parser.add_argument(
        "--alias",
        type=str,
        required=True,
        help="Alias used for exploit identification, analytics and as a key for tracking repeated flag IDs.",
    )
    parser.add_argument(
        "--command",
        type=str,
        required=True,
        help="Command that runs the exploit (must contain '[ip]' placeholder).",
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
        help="Scope of the `flag_ids` dictionary.",
    )
    parser.add_argument(
        "--prepare",
        type=str,
        help="Optional shell command to run before starting the first attack.",
    )
    parser.add_argument(
        "--cleanup",
        type=str,
        help="Optional shell command to run after completing the last attack.",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        default=False,
        help="Toggle draft mode (Do not skip attacks that use already used flag ids).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=128,
        help="Maximum number of parallel workers for running the attacks.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Timeout in seconds after which the exploit will be terminated if it's stuck or takes too long to complete.",
    )

    args = parser.parse_args()
    main(args)

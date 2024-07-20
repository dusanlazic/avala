import os
import json
from shared.logs import logger
from client.executor.python import import_func, match_flags
from client.api import client
from client.config import load_user_config


def attack(script, target, service=None):
    if script.endswith(".py"):
        script = script[:-3]

    execute_attack = None

    try:
        execute_attack = import_func(script, "exploit")
    except ModuleNotFoundError:
        logger.error(
            "Exploit module <bold>%s.py</> not found. Please make sure the file exists and it's under <bold>%s.</>"
            % (script, os.getcwd())
        )
    except AttributeError:
        logger.error(
            "Required exploit function not found within <bold>%s.py</>. Please make sure the module contains the <bold>exploit</> function."
            % script
        )

    if not execute_attack:
        exit(1)

    logger.debug(f"Imported exploit: {script}")

    try:
        client.import_settings()
        logger.debug("Imported client settings.")
    except FileNotFoundError:
        logger.debug("No client settings found. Connecting to the server.")
        load_user_config()
        client.connect()
        client.export_settings()

    logger.debug(client.game)

    if target.lower() == "nop":
        logger.debug("Using NOP team IP: %s." % client.game.nop_team_ip)
        target = client.game.nop_team_ip
    elif target.lower() in ["self", "own", "team"]:
        logger.debug("Using team IP: %s." % client.game.team_ip)
        target = client.game.team_ip[0]

    flag_ids = client.get_flag_ids().services[service][target] if service else None

    if flag_ids:
        logger.debug(f"Fetched flag IDs:\n{json.dumps(flag_ids, indent=2)}")

    try:
        result = execute_attack(target, flag_ids)
        flags = match_flags(client.game.flag_format, result)
        if not flags:
            logger.warning(
                "No flags retrieved from attacking <bold>%s</> via <bold>%s</>."
                % (target, script)
            )

        logger.success(
            f"Retrieved %d flags from attacking <bold>%s</> via <bold>%s</>."
            % (len(flags), target, script)
        )

        print("\n".join(flags))

        client.enqueue(flags, script, target)

    except Exception as e:
        logger.error(
            f"An error has occured while attacking <bold>{target}</> via <bold>{script}</>: {e}"
        )
        return

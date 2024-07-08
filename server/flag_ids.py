import os
import sys
import json
import time
import hashlib
from importlib import import_module, reload
from shared.logs import logger
from .config import config
from .state import set_state, get_state


def reload_flag_ids():
    logger.debug("Reloading flag ids")

    fetch, process = import_user_functions()

    flag_ids_updated = False

    attempts = 0

    while not flag_ids_updated:
        time.sleep(1)
        if attempts > 2:
            break

        teams_json = fetch()

        teams_json_norm = normalize_dict(teams_json)
        teams_json_str = json.dumps(teams_json_norm)
        teams_json_hash = hashlib.md5(teams_json_str.encode()).hexdigest()

        old_teams_json_hash = get_state("teams_json_hash")

        flag_ids_updated = (
            old_teams_json_hash == teams_json_hash or old_teams_json_hash is None
        )

        attempts += 1

    set_state("teams_json_hash", teams_json_hash)

    logger.debug("Updated state %s" % teams_json_hash)

    processed_flag_ids = process(teams_json)
    set_state("flag_ids", json.dumps(processed_flag_ids))

    logger.debug("Updated state flag_ids")


def normalize_dict(data):
    """Recursively sort and normalize dictionary data."""
    if isinstance(data, dict):
        return {key: normalize_dict(value) for key, value in sorted(data.items())}
    elif isinstance(data, list):
        return sorted(normalize_dict(item) for item in data)
    else:
        return data


def compare_dicts(dict1, dict2):
    """Compare two dictionaries."""
    return normalize_dict(dict1) == normalize_dict(dict2)


def import_user_functions():
    """Imports and reloads the fetch and process functions that fetch and process teams.json file."""
    module_name = "flag_ids"

    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.append(cwd)

    imported_module = reload(import_module(module_name))

    fetch_function = getattr(imported_module, "fetch_json")
    process_function = getattr(imported_module, "process_json")

    return fetch_function, process_function

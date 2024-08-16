import os
import sys
import json
import time
import hashlib
import asyncio
from importlib import import_module, reload
from .shared.logs import logger
from .state import StateManager
from .config import config
from .database import get_db


attack_data_updated_event: asyncio.Event = asyncio.Event()


def reload_attack_data():
    attack_data_updated_event.clear()

    fetch_json, process_json = import_user_functions()

    if not fetch_json or not process_json:
        return

    with get_db() as db, StateManager(db) as state:
        old_json_hash = state.attack_data_hash

        json_updated = False
        attempts_left = config.attack_data.max_attempts

        while not json_updated:
            try:
                new_json = fetch_json()
            except Exception as e:
                attempts_left -= 1
                logger.error("An error occurred while fetching attack data: %s" % e)
                logger.info(
                    "Retrying in %ds, %d attempts left."
                    % (config.attack_data.retry_interval, attempts_left)
                )
                time.sleep(config.attack_data.retry_interval)
                if not attempts_left:
                    logger.warning(
                        "It seems that your <b>%s.py</> module is not working properly. Please check it."
                        % config.attack_data.module
                    )
                    break
                continue

            new_json_norm = normalize_dict(new_json)
            new_json_str = json.dumps(new_json_norm)
            new_json_hash = hashlib.md5(new_json_str.encode()).hexdigest()

            json_updated = new_json_hash != old_json_hash or old_json_hash is None

            if not json_updated and attempts_left:
                attempts_left -= 1
                logger.info(
                    "Fetched old attack data (<yellow>%s</>). Retrying in %ds, %d attempts left."
                    % (
                        old_json_hash[:8],
                        config.attack_data.retry_interval,
                        attempts_left,
                    )
                )
                time.sleep(config.attack_data.retry_interval)
            else:
                break

        if json_updated:
            logger.info(
                "Fetched new attack data (<yellow>%s</> -> <green>%s</>)."
                % (str(old_json_hash)[:8], new_json_hash[:8])
            )

            processed_attack_data = process_json(new_json)

            state.attack_data_hash = new_json_hash
            state.attack_data = json.dumps(processed_attack_data)
        elif old_json_hash:
            logger.info(
                "Reusing old attack data (<yellow>%s</>) to avoid wasting tick time."
                % old_json_hash[:8]
            )
        else:
            logger.error(
                "Failed to fetch attack data. Please fix your <b>fetch</> function in your <b>%s.py</> module."
                % config.attack_data.module
            )
            return

    attack_data_updated_event.set()


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
    """Imports and reloads the fetch and process functions that fetch and process attack data json file."""
    module_name = config.attack_data.module

    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.append(cwd)

    try:
        imported_module = reload(import_module(module_name))
    except Exception as e:
        logger.error("Unable to load module <b>%s</>: %s" % (module_name, e))
        return None, None

    fetch_json = getattr(imported_module, "fetch_json", None)
    if not fetch_json:
        logger.error(
            "Function <b>fetch_json</> not found in module <b>%s</>." % module_name
        )

    process_json = getattr(imported_module, "process_json", None)
    if not process_json:
        logger.error(
            "Function <b>process_json</> not found in module <b>%s</>." % module_name
        )

    return fetch_json, process_json

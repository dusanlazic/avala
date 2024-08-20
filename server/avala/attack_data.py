import os
import sys
import json
import time
import hashlib
import asyncio
from typing import Any
from importlib import import_module, reload
from .shared.logs import logger
from .state import StateManager
from .config import config
from .database import get_db


attack_data_updated_event: asyncio.Event = asyncio.Event()


def reload_attack_data():
    """
    Reloads and updates the attack data by fetching and processing new JSON data using user-defined functions,
    comparing it against the current data (by comparing hashes), and updating if new data is found. When data
    is updated, the event `attack_data_updated_event` is set, signaling clients that new data is available.
    """
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
                logger.error(
                    "An error occurred while fetching attack data: {error}", error=e
                )
                logger.info(
                    "Retrying in {interval}s, {attempts} attempts left.",
                    interval=config.attack_data.retry_interval,
                    attempts=attempts_left,
                )
                time.sleep(config.attack_data.retry_interval)
                if not attempts_left:
                    logger.warning(
                        "It seems that your <b>{module}.py</> module is not working properly. Please check it.",
                        module=config.attack_data.module,
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
                    "Fetched old attack data (<yellow>{hash}</>). Retrying in {interval}s, {attempts} attempts left.",
                    hash=old_json_hash[:8],
                    interval=config.attack_data.retry_interval,
                    attempts=attempts_left,
                )
                time.sleep(config.attack_data.retry_interval)
            else:
                break

        if json_updated:
            logger.info(
                "Fetched new attack data (<yellow>{old_hash}</> -> <green>{new_hash}</>).",
                old_hash=str(old_json_hash)[:8],
                new_hash=new_json_hash[:8],
            )

            processed_attack_data = process_json(new_json)

            state.attack_data_hash = new_json_hash
            state.attack_data = json.dumps(processed_attack_data)
        elif old_json_hash:
            logger.info(
                "Reusing old attack data (<yellow>{hash}</>) to avoid wasting tick time.",
                hash=old_json_hash[:8],
            )
        else:
            logger.error(
                "Failed to fetch attack data. Please fix your <b>fetch</> function in your <b>{module}.py</> module.",
                module=config.attack_data.module,
            )
            return

    attack_data_updated_event.set()


def normalize_dict(data: dict | list | Any) -> dict | list | Any:
    """
    Recursively sort keys and items in a dictionary. This is useful for not mistaking
    a differently ordered dictionary as a different one, which sometimes happens with
    attack.json / teams.json files.
    """
    if isinstance(data, dict):
        return {key: normalize_dict(value) for key, value in sorted(data.items())}
    elif isinstance(data, list):
        return sorted(normalize_dict(item) for item in data)
    else:
        return data


def import_user_functions():
    """
    Imports and reloads the fetch and process functions that fetch and process attack data.
    """
    module_name = config.attack_data.module

    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.append(cwd)

    try:
        imported_module = reload(import_module(module_name))
    except Exception as e:
        logger.error(
            "Unable to load module <b>{module}</>: {error}",
            module=module_name,
            error=e,
        )
        return None, None

    fetch_json = getattr(imported_module, "fetch_json", None)
    if not fetch_json:
        logger.error(
            "Function <b>fetch_json</> not found in module <b>{module}</>.",
            module=module_name,
        )

    process_json = getattr(imported_module, "process_json", None)
    if not process_json:
        logger.error(
            "Function <b>process_json</> not found in module <b>{module}</>.",
            module=module_name,
        )

    return fetch_json, process_json

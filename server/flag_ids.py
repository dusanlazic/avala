import os
import sys
import json
import hashlib
import asyncio
from importlib import import_module, reload
from .state import state


flag_ids_updated_event: asyncio.Event = asyncio.Event()


def reload_flag_ids():
    fetch_json, process_json = import_user_functions()

    json_updated = False
    while not json_updated:
        new_json = fetch_json()

        new_json_norm = normalize_dict(new_json)
        new_json_str = json.dumps(new_json_norm)
        new_json_hash = hashlib.md5(new_json_str.encode()).hexdigest()

        old_json_hash = state.teams_json_hash

        json_updated = new_json_hash != old_json_hash or old_json_hash is None
        break

    processed_flag_ids = process_json(new_json)

    state.teams_json_hash = new_json_hash
    state.flag_ids = json.dumps(processed_flag_ids)

    flag_ids_updated_event.set()
    flag_ids_updated_event.clear()


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

    fetch_json = getattr(imported_module, "fetch_json")
    process_json = getattr(imported_module, "process_json")

    return fetch_json, process_json

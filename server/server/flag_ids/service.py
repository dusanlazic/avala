import asyncio
import hashlib
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType
from typing import Any

from avala.common.config import config
from avala.common.logger import logger

from database import Database, StateManager, get_async_db_session

flag_ids_updated_event: asyncio.Event = asyncio.Event()


async def get_flag_ids(db: Database) -> dict | None:
    """
    Loads the flag IDs from the database.
    """
    async with StateManager(db) as state:
        flag_ids = await state.get("flag_ids")
        return json.loads(flag_ids) if flag_ids else None


def normalize_dict(data: dict | list | Any) -> dict | list | Any:
    """
    Recursively sort keys and items in a dictionary. This is useful for not mistaking
    a differently ordered dictionary as a different one, which sometimes happens with
    attack.json / teams.json files.

    Note: It doesn't handle lists of "unsortable" items (e.g. lists of dictionaries).
    Function will return such lists without sorting them.
    """
    if isinstance(data, dict):
        return {key: normalize_dict(value) for key, value in sorted(data.items())}
    elif isinstance(data, list):
        normalized_list = [normalize_dict(item) for item in data]
        try:
            return sorted(normalized_list)
        except TypeError:
            # If sorting is not possible, return the list as is
            return normalized_list
    else:
        return data


def import_flag_ids_module() -> ModuleType:
    """
    Dynamically imports the flag IDs fetching module.
    """
    script_path = config.flag_ids.script_path
    module_name = "flag_ids_script"

    spec = spec_from_file_location(module_name, script_path)
    if spec and spec.loader:
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[module_name] = module
        return module

    raise ImportError("Failed to import the flag IDs fetching module.")


async def reload_flag_ids() -> None:
    """
    Reloads and updates the flag IDs data by fetching and processing new JSON data using user-defined functions,
    comparing it against the current data (by comparing hashes), and updating if new data is found. When data
    is updated, the event `flag_ids_updated_event` is set, signaling clients that new data is available through
    long polling.
    """
    flag_ids_updated_event.clear()

    module = import_flag_ids_module()
    fetch = getattr(module, "fetch", None)
    process = getattr(module, "process", None)

    if not fetch or not process:
        logger.error(
            "Function <b>fetch</> or <b>process</> not found in module <b>{module}</>.",
            module=config.flag_ids.script_path,
        )
        flag_ids_updated_event.set()
        return

    async with get_async_db_session() as db, StateManager(db) as state:
        old_data_hash = await state.get("flag_ids_hash")
        attempts_left = config.flag_ids.retries
        flag_ids_updated = False

        while attempts_left and not flag_ids_updated:
            try:
                new_data = await asyncio.get_event_loop().run_in_executor(None, fetch)  # TODO: Support async fetch
            except Exception as e:
                attempts_left -= 1
                logger.error("An error occurred while fetching attack data: {error}", error=e)
                if attempts_left:
                    logger.info(
                        "Retrying in {interval}s, {attempts} attempts left.",
                        interval=config.flag_ids.interval.total_seconds(),
                        attempts=attempts_left,
                    )
                    await asyncio.sleep(config.flag_ids.interval.total_seconds())
                else:
                    logger.warning(
                        "It seems that your <b>{module}</> module is not working properly. Please check it.",
                        module=config.flag_ids.script_path,
                    )

            new_data_normalized = normalize_dict(new_data)
            new_data_dump = json.dumps(new_data_normalized)
            new_data_hash = hashlib.md5(new_data_dump.encode()).hexdigest()

            flag_ids_updated = new_data_hash != old_data_hash or old_data_hash is None

            if not flag_ids_updated and attempts_left:
                attempts_left -= 1
                logger.info(
                    "Fetched old attack data (<yellow>{hash}</>). Retrying in {interval}s, {attempts} attempts left.",
                    hash=old_data_hash[:8],
                    interval=config.flag_ids.interval.total_seconds(),
                    attempts=attempts_left,
                )
                await asyncio.sleep(config.flag_ids.interval.total_seconds())

        if flag_ids_updated:
            logger.info(
                "Fetched new flag IDs (<yellow>{old_hash}</> -> <green>{new_hash}</>).",
                old_hash=str(old_data_hash)[:8],
                new_hash=new_data_hash[:8],
            )
            await state.set("flag_ids", json.dumps(process(new_data)))
            await state.set("flag_ids_hash", new_data_hash)
        elif old_data_hash:
            logger.info(
                "Unable to fetch new flag IDs. Reusing old data (<yellow>{hash}</>).",
                hash=old_data_hash[:8],
            )
        else:
            logger.error(
                "It seems that your <b>{module}</> module is not working properly. Please check it.",
                module=config.flag_ids.script_path,
            )

        flag_ids_updated_event.set()

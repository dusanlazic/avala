import asyncio
import json

from database import Database, StateManager

flag_ids_updated_event: asyncio.Event = asyncio.Event()


async def get_flag_ids(db: Database) -> dict | None:
    """
    Fetches the flag IDs from the database.
    """
    async with StateManager(db) as state:
        flag_ids = await state.get("flag_ids")
        return json.loads(flag_ids) if flag_ids else None

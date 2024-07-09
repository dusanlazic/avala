from shared.logs import logger
from shared.util import colorize
from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from server.auth import basic_auth
from server.models import Flag
from server.database import db
from server.mq.rabbit_async import rabbit
from server.scheduler import get_tick_number
from server.config import config

router = APIRouter(prefix="/flags", tags=["Flags"])


class EnqueueBody(BaseModel):
    values: list[str]
    exploit: str
    target: str


@router.post("/queue")
async def enqueue(
    flags: EnqueueBody,
    bg: BackgroundTasks,
    username: Annotated[str, Depends(basic_auth)],
):
    with db.connection_context():
        duplicate_flags = Flag.select(Flag.value).where(Flag.value.in_(flags.values))
        dup_flag_values = {flag.value for flag in duplicate_flags}
        new_flag_values = list(set(flags.values) - dup_flag_values)

        current_tick = get_tick_number()

        Flag.insert_many(
            [
                {
                    "value": value,
                    "exploit": flags.exploit,
                    "target": flags.target,
                    "tick": current_tick,
                    "player": username,
                    "status": "queued",
                }
                for value in new_flag_values
            ]
        ).on_conflict_ignore().execute()

    for flag in new_flag_values:
        bg.add_task(rabbit.queues.submission_queue.put, flag, ttl=config.game.flag_ttl)

    logger.info(
        "📥 <bold>%d</> flags from <bold>%s</> via <bold>%s</> by <bold>%s</> (<green>%d</> new, <yellow>%d</> duplicates)."
        % (
            len(flags.values),
            colorize(flags.target),
            colorize(flags.exploit),
            username,
            len(new_flag_values),
            len(dup_flag_values),
        )
    )

    return {
        "discarded": len(dup_flag_values),
        "enqueued": len(new_flag_values),
    }

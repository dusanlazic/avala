from shared.logs import logger
from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from server.auth import basic_auth
from server.models import Flag
from server.database import db
from server.mq.rabbit_async import rabbit
from server.scheduler import get_tick_number

router = APIRouter(prefix="/flags", tags=["Flags"])


class EnqueueBody(BaseModel):
    values: list[str]
    exploit: str
    player: str
    target: str


@router.post("/queue")
async def enqueue(
    flags: EnqueueBody,
    bg: BackgroundTasks,
    _: Annotated[str, Depends(basic_auth)],
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
                    "player": flags.player,
                    "status": "queued",
                }
                for value in new_flag_values
            ]
        ).on_conflict_ignore().execute()

    for flag in new_flag_values:
        bg.add_task(rabbit.queues.submission_queue.put, flag)

    logger.info(
        "<bold>%d</bold> flags from <bold>%s</bold> using <bold>%s, %s</bold> -> <green>%d new</green> - <yellow>%d duplicates</yellow>."
        % (
            len(flags.values),
            flags.target,
            flags.exploit,
            flags.player,
            len(new_flag_values),
            len(dup_flag_values),
        )
    )

    return {"discarded": dup_flag_values, "enqueued": new_flag_values}

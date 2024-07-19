import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from server.auth import basic_auth
from server.models import Flag
from server.database import get_db
from server.mq.rabbit_async import rabbit
from server.scheduler import get_tick_number
from server.config import config
from server.broadcast import broadcast
from shared.logs import logger
from shared.util import colorize
from typing import Annotated

router = APIRouter(prefix="/flags", tags=["Flags"])


class EnqueueBody(BaseModel):
    values: list[str]
    exploit: str
    target: str


@router.post("/queue")
async def enqueue(
    flags: EnqueueBody,
    bg: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    username: Annotated[str, Depends(basic_auth)],
):
    current_tick = get_tick_number()
    existing_flags = db.query(Flag.value).filter(Flag.value.in_(flags.values)).all()
    dup_flag_values = {flag.value for flag in existing_flags}
    new_flag_values = list(set(flags.values) - dup_flag_values)

    new_flags = [
        Flag(
            value=value,
            exploit=flags.exploit,
            target=flags.target,
            tick=current_tick,
            player=username,
            status="queued",
        )
        for value in new_flag_values
    ]
    db.bulk_save_objects(new_flags)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()

    for flag in new_flag_values:
        bg.add_task(rabbit.queues.submission_queue.put, flag, ttl=config.game.flag_ttl)

    await broadcast.publish(
        channel="flag_reports",
        message={
            "target": flags.target,
            "exploit": flags.exploit,
            "player": username,
            "duplicates": len(dup_flag_values),
            "enqueued": len(new_flag_values),
        },
    )

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

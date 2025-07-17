import asyncio

import aio_pika
from avala.common.clock import get_tick_number
from sqlalchemy import select

from server.database import Database, broadcast
from server.messaging import Channel

from ..stats.schemas import FlagUpdateMessage
from .models import Flag


async def enqueue_flags(
    values: set[str],
    host: str,
    service: str | None,
    worker: str | None,
    exploit: str | None,
    db: Database,
    ch: Channel,
):
    dup_flag_values = (await db.execute(select(Flag.value).where(Flag.value.in_(values)))).scalars().all()
    new_flag_values = values - set(dup_flag_values)

    if not new_flag_values:
        if dup_flag_values:
            # Stream live data to dashboard
            await broadcast.publish(
                channel="flags",
                message=FlagUpdateMessage(
                    host=host,
                    service=service,
                    exploit=exploit,
                    status="discarded",
                    delta=len(dup_flag_values),
                ).model_dump_json(),
            )

        return 0, len(dup_flag_values)

    # Persist the new flags in the database
    current_tick = get_tick_number()
    db.add_all(
        [
            Flag(
                value=value,
                host=host,
                service=service,
                worker=worker,
                exploit=exploit,
                tick=current_tick,
            )
            for value in new_flag_values
        ]
    )
    await db.commit()

    # Stream live data to dashboard
    await broadcast.publish(
        channel="flags",
        message=FlagUpdateMessage(
            host=host,
            service=service,
            exploit=exploit,
            status="queued",
            delta=len(new_flag_values),
        ).model_dump_json(),
    )

    # Publish the new flags for processing
    messages = [
        ch.default_exchange.publish(
            aio_pika.Message(
                value.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="flag.submission",
        )
        for value in new_flag_values
    ]
    await asyncio.gather(*messages)

    return len(new_flag_values), len(dup_flag_values)

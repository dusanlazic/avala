import asyncio

import aio_pika
from avala.common.clock import get_tick_number
from sqlalchemy import select

from server.database import Database
from server.messaging import Channel

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

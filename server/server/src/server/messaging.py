from typing import Annotated

import aio_pika
from avala.common.config import config
from avala.common.logger import logger
from fastapi import Depends, Request


async def connect_to_rabbitmq() -> tuple[
    aio_pika.abc.AbstractRobustConnection | None, aio_pika.abc.AbstractChannel | None
]:
    """
    Connects to RabbitMQ using the configuration settings and returns the connection and channel objects.
    """
    # TODO: Move to common?
    try:
        connection = await aio_pika.connect_robust(
            host=config.rabbitmq.host,
            port=config.rabbitmq.port,
            login=config.rabbitmq.user,
            password=config.rabbitmq.password,
        )
        channel = await connection.channel()
        logger.success("Connected to RabbitMQ.")
        return connection, channel
    except Exception as e:
        logger.error(
            "Failed to connect to RabbitMQ. <b>{error}</>: {error_msg}",
            error=type(e).__name__,
            error_msg=e,
        )

    return None, None


async def declare_submission_queue(channel: aio_pika.abc.AbstractChannel) -> aio_pika.abc.AbstractQueue:
    # TODO: Move to common?
    return await channel.declare_queue(
        "flag.submission",
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-delivery-limit": config.submitter.retries,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "flag.submission.dlq",
        },
    )


async def get_channel(request: Request) -> aio_pika.abc.AbstractChannel:
    """
    Dependency to get the RabbitMQ channel from the request state.
    """
    if not hasattr(request.app.state, "channel"):
        raise RuntimeError("RabbitMQ channel not initialized.")
    return request.app.state.channel


Channel = Annotated[aio_pika.abc.AbstractChannel, Depends(get_channel)]

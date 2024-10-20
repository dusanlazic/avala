from typing import Callable

import aio_pika
from aio_pika import Channel, IncomingMessage, Message, RobustConnection
from avala_shared.logs import logger

from ..config import config


class RabbitQueue:
    """
    Simple async wrapper around a RabbitMQ queue.
    """

    def __init__(
        self,
        channel: Channel,
        routing_key: str,
        exchange: str = "",
        exchange_type: str = "direct",
        durable: bool = False,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: dict = None,
    ) -> None:
        self.channel: Channel = channel
        self.routing_key: str = routing_key
        self.exchange: str = exchange

        # Queue cannot be declared in the constructor because it's an
        # async operation. Instead, it's declared upon connecting.
        self.exchange_type: str = exchange_type
        self.durable: bool = durable
        self.exclusive: bool = exclusive
        self.auto_delete: bool = auto_delete
        self.arguments: dict = arguments

    async def declare(self) -> "RabbitQueue":
        queue = await self.channel.declare_queue(
            self.routing_key,
            durable=self.durable,
            exclusive=self.exclusive,
            auto_delete=self.auto_delete,
            arguments=self.arguments,
        )
        logger.info("Declared queue {routing_key}.", routing_key=self.routing_key)

        if self.exchange:
            await self.channel.declare_exchange(
                name=self.exchange,
                type=self.exchange_type,
                durable=True,
            )
            await queue.bind(
                exchange=self.exchange,
                routing_key=self.routing_key,
            )
            logger.info(
                "Declared exchange {exchange} of type {type}.",
                exchange=self.exchange,
                type=self.exchange_type,
            )

        return self

    async def put(self, message: str, ttl: str = None):
        """
        Publishes a message to the queue.

        :param message: Content of the message.
        :type message: str
        :param ttl: Message expiration policy expressed in milliseconds as string, defaults to None.
        :type ttl: int, optional
        """
        exchange = (
            await self.channel.get_exchange(self.exchange)
            if self.exchange
            else self.channel.default_exchange
        )

        await exchange.publish(
            routing_key=self.routing_key,
            message=Message(
                body=message.encode(),
                expiration=int(ttl) // 1000 if ttl else None,
            ),
        )

    async def get(self):
        """
        Performs a basic get operation on the queue.
        """
        queue = await self.channel.get_queue(
            name=self.routing_key,
            ensure=True,
        )
        return await queue.get()

    async def size(self):
        """
        Returns the number of messages in the queue.

        :return: Number of messages in the queue.
        :rtype: int
        """
        queue = await self.channel.get_queue(
            name=self.routing_key,
            ensure=True,
        )
        return queue.declaration_result.message_count

    async def add_consumer(self, callback: Callable):
        queue = await self.channel.get_queue(
            name=self.routing_key,
            ensure=True,
        )
        await queue.consume(callback)


class RabbitConnection:
    def __init__(self, silent: bool = False) -> None:
        self.connection: RobustConnection
        self.channel: Channel
        self.queues: dict[str, RabbitQueue] = {}

        self.silent = silent

    async def connect(self):
        self.connection = await aio_pika.connect_robust(
            host=config.rabbitmq.host,
            port=config.rabbitmq.port,
            login=config.rabbitmq.user,
            password=config.rabbitmq.password,
        )
        self.channel = await self.connection.channel()

        if not self.silent:
            logger.info("Connected to RabbitMQ.")

    async def close(self):
        if not self.channel.is_closed:
            await self.channel.close()
        if not self.connection.is_closed:
            await self.connection.close()

        if not self.silent:
            logger.info("Closed RabbitMQ connection.")

    async def ack(self, message: IncomingMessage, multiple: bool = False):
        """
        Acknowledges a single or multiple messages.

        :param message: Message to acknowledge.
        :type message: IncomingMessage
        :param multiple: Acknowledge messages up to and including the provided message, defaults to False.
        :type multiple: bool, optional
        """
        await message.ack(multiple=multiple)

    async def reject(self, message: IncomingMessage, requeue: bool = False):
        """
        Rejects a message and optionally requeues it.

        :param message: Message to reject.
        :type message: IncomingMessage
        :param requeue: Requeue the message, defaults to False.
        :type requeue: bool, optional
        """
        await message.reject(requeue=requeue)

    def add_queue(self, queue: RabbitQueue):
        self.queues[queue.routing_key] = queue

    def get_queue(self, routing_key: str):
        return self.queues.get(routing_key, None)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


rabbit = RabbitConnection()

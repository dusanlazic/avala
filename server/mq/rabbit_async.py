import aio_pika
from addict import Dict
from aio_pika.abc import AbstractChannel
from ..config import config
from shared.logs import logger


class RabbitQueue:
    """A simple wrapper around a RabbitMQ queue."""

    def __init__(self, channel, routing_key, durable=False) -> None:
        self.channel: AbstractChannel = channel
        self.routing_key = routing_key
        self.durable = durable

    async def declare(self):
        await self.channel.declare_queue(self.routing_key, durable=self.durable)
        logger.info(f"Declared queue {self.routing_key}.")

    async def put(self, message, ttl=None):
        await self.channel.default_exchange.publish(
            aio_pika.Message(body=message.encode(), expiration=ttl),
            routing_key=self.routing_key,
        )

    async def ack(self, delivery_tag, multiple=False):
        await self.channel.basic_ack(delivery_tag=delivery_tag, multiple=multiple)

    async def add_consumer(self, callback):
        await self.channel.set_qos(prefetch_count=0)
        await self.channel.consume(callback, queue=self.routing_key)

    async def size(self):
        queue = await self.channel.declare_queue(self.routing_key, passive=True)
        return queue.declaration_result.message_count


class RabbitConnection:
    def __init__(self) -> None:
        self.connection = None
        self.channel = None

        self.queues = Dict()

    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(
                host=config.rabbitmq.host,
                port=config.rabbitmq.port,
                login=config.rabbitmq.user,
                password=config.rabbitmq.password,
            )
            self.channel = await self.connection.channel()
            logger.info("Connected to RabbitMQ.")
        except Exception as e:
            logger.error(f"Error connecting to RabbitMQ: {e}")

    async def close(self):
        if not self.channel.is_closed:
            await self.channel.close()
        if not self.connection.is_closed:
            await self.connection.close()

        self.channel = None
        self.connection = None
        logger.info("Closed RabbitMQ connection.")

    async def create_queue(self, routing_key, durable=False):
        queue = RabbitQueue(self.channel, routing_key, durable=durable)
        await queue.declare()
        self.queues[routing_key] = queue
        return queue

    def add_queue(self, queue: RabbitQueue):
        self.queues[queue.routing_key] = queue


rabbit = RabbitConnection()

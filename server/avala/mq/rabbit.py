from typing import Callable

import pika
from pika import BlockingConnection
from pika.adapters.blocking_connection import BlockingChannel

from ..config import config
from ..shared.logs import logger


class RabbitQueue:
    """
    Simple wrapper around a RabbitMQ queue.
    """

    def __init__(
        self,
        channel: BlockingChannel,
        routing_key: str,
        exchange: str = "",
        exchange_type: str = "direct",
        durable: bool = False,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: dict = None,
        silent: bool = False,
    ) -> None:
        self.channel: BlockingChannel = channel
        self.routing_key: str = routing_key
        self.exchange: str = exchange

        self.silent = silent

        self.channel.queue_declare(
            queue=self.routing_key,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            arguments=arguments,
        )
        if not self.silent:
            logger.info("Declared queue {routing_key}.", routing_key=self.routing_key)

        if self.exchange:
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type=exchange_type,
                durable=True,
            )
            self.channel.queue_bind(
                queue=self.routing_key,
                exchange=self.exchange,
            )
            if not self.silent:
                logger.info(
                    "Declared exchange {exchange} of type {type}.",
                    exchange=self.exchange,
                    type=exchange_type,
                )

    def put(self, message: str, ttl: str = None):
        """
        Publishes a message to the queue.

        :param message: Content of the message.
        :type message: str
        :param ttl: Message expiration policy expressed in milliseconds as string, defaults to None.
        :type ttl: str, optional
        """
        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=self.routing_key,
            body=message,
            properties=pika.BasicProperties(expiration=ttl),
        )

    def get(self):
        """
        Performs a basic get operation on the queue.
        """
        return self.channel.basic_get(queue=self.routing_key)

    def size(self) -> int:
        """
        Returns the number of messages in the queue.

        :return: Number of messages in the queue.
        :rtype: int
        """
        return self.channel.queue_declare(
            queue=self.routing_key,
            passive=True,
        ).method.message_count

    def add_consumer(self, callback: Callable):
        self.channel.basic_consume(queue=self.routing_key, on_message_callback=callback)


class RabbitConnection:
    def __init__(self, silent: bool = False) -> None:
        self.connection: BlockingConnection
        self.channel: BlockingChannel
        self.queues: dict[str, RabbitQueue] = {}

        self.silent = silent

    def connect(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=config.rabbitmq.host,
                port=config.rabbitmq.port,
                credentials=pika.PlainCredentials(
                    config.rabbitmq.user,
                    config.rabbitmq.password,
                ),
            )
        )
        self.channel = self.connection.channel()

        if not self.silent:
            logger.info("Connected to RabbitMQ.")

    def close(self):
        if not self.channel.is_closed:
            self.channel.close()
        if not self.connection.is_closed:
            self.connection.close()

        if not self.silent:
            logger.info("Closed RabbitMQ connection.")

    def ack(self, delivery_tag: int, multiple: bool = False):
        """
        Acknowledges a single or multiple messages.

        :param delivery_tag: Delivery tag of the message to acknowledge.
        :type delivery_tag: int
        :param multiple: Acknowledge messages up to and including the provided delivery tag, defaults to False.
        :type multiple: bool, optional
        """
        self.channel.basic_ack(delivery_tag=delivery_tag, multiple=multiple)

    def reject(self, delivery_tag: int, requeue: bool = False):
        """
        Rejects a message and optionally requeues it.

        :param delivery_tag: Delivery tag of the message to reject.
        :type delivery_tag: int
        :param requeue: Requeue the message, defaults to False.
        :type requeue: bool, optional
        """
        self.channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)

    def add_queue(self, queue: RabbitQueue):
        self.queues[queue.routing_key] = queue

    def get_queue(self, routing_key: str):
        return self.queues.get(routing_key, None)

    def start_consuming(self):
        self.channel.start_consuming()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


rabbit = RabbitConnection()

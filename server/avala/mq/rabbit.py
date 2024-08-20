import pika
from ..config import config
from ..shared.logs import logger


class RabbitQueue:
    """
    Simple wrapper around a RabbitMQ queue.
    """

    def __init__(self, channel, routing_key, durable=False) -> None:
        self.channel = channel
        self.routing_key = routing_key

        self.channel.queue_declare(queue=self.routing_key, durable=durable)
        logger.info("Declared queue {routing_key}.", routing_key=self.routing_key)

    def put(self, message):
        self.channel.basic_publish(
            exchange="", routing_key=self.routing_key, body=message
        )

    def ack(self, delivery_tag, multiple=False):
        self.channel.basic_ack(delivery_tag=delivery_tag, multiple=multiple)

    def add_consumer(self, callback):
        self.channel.basic_consume(queue=self.routing_key, on_message_callback=callback)

    def size(self):
        return self.channel.queue_declare(
            queue=self.routing_key, passive=True
        ).method.message_count


class RabbitConnection:
    def __init__(self) -> None:
        self.connection = None
        self.channel = None

    def connect(self):
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=config.rabbitmq.host,
                    port=config.rabbitmq.port,
                    credentials=pika.PlainCredentials(
                        config.rabbitmq.user, config.rabbitmq.password
                    ),
                )
            )
            self.channel = self.connection.channel()
            logger.info("Connected to RabbitMQ.")
        except Exception as e:
            logger.error("Error connecting to RabbitMQ: {error}", error=e)

    def close(self):
        if not self.channel.is_closed:
            self.channel.close()
        if not self.connection.is_closed:
            self.connection.close()

        self.channel = None
        self.connection = None
        logger.info("Closed RabbitMQ connection.")


rabbit = RabbitConnection()

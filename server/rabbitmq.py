import pika
from .config import config

channel = None


def connect_rabbitmq():
    global channel
    channel = get_channel()


def get_channel():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=config.rabbitmq.host,
            port=config.rabbitmq.port,
            credentials=pika.PlainCredentials(
                config.rabbitmq.user, config.rabbitmq.password
            ),
        )
    )

    return connection.channel()


class RabbitMQQueue:
    """A simple wrapper around a RabbitMQ queue."""

    def __init__(self, channel, routing_key, durable=False) -> None:
        self.channel = channel
        self.routing_key = routing_key

        self.channel.queue_declare(queue=self.routing_key, durable=durable)

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

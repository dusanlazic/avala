import pika
from shared.logs import logger
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Dict
from datetime import datetime
from ..models import Flag, FlagResponse
from ..config import load_user_config
from ..database import db, connect_database
from ..rabbitmq import RabbitMQQueue, connect_rabbitmq, channel
from ..scheduler import get_tick_duration, get_next_tick_start


def main():
    load_user_config()
    connect_database()
    connect_rabbitmq()

    scheduler = BackgroundScheduler()
    worker = Persister(scheduler, channel)
    worker.start()


class Persister:
    def __init__(self, scheduler: BackgroundScheduler, channel) -> None:
        self.scheduler = scheduler
        self.channel = channel

        self.persisting_buffer: list[FlagResponse] = []
        self.persisting_queue = RabbitMQQueue(self.channel, "persisting_queue")

        self._initialize()

    def start(self):
        logger.info("Waiting for flag responses...")

        self.scheduler.start()
        self.channel.start_consuming()

    def _initialize(self):
        """Initializes and configures threads, consumers and scheduled jobs for flag response persistence based on the configuration."""
        now = datetime.now()
        tick_duration = get_tick_duration()
        next_tick_start = get_next_tick_start(now)

        self.persisting_queue.add_consumer(self._persist_responses_in_batches_consumer)
        self.scheduler.add_job(
            func=self._persist_responses,
            trigger="interval",
            seconds=tick_duration.total_seconds(),
            id="submitter",
            next_run_time=next_tick_start,
        )

    def _persist_responses_in_batches_consumer(self, ch, method, properties, body):
        """Receives responses from the persisting queue and initiates persisting of a batch of queued flags."""
        self.persisting_buffer.append(FlagResponse.deserialize(body.decode()))
        if len(self.persisting_buffer) >= 50:  # temporary hardcoded
            self._persist_responses()
            ch.basic_ack(delivery_tag=method.delivery_tag, multiple=True)
            self.persisting_buffer.clear()

    def _persist_responses(self):
        """Persists responses from the persistence buffer into the database."""
        flag_responses_map: Dict[str, FlagResponse] = {}

        if not self.persisting_buffer:
            return

        logger.info("Persisting %d flag responses..." % len(self.persisting_buffer))

        for flag_response in self.persisting_buffer:
            flag_responses_map[flag_response.value] = flag_response

        with db.atomic():
            flag_records_to_update = Flag.select().where(
                Flag.value.in_(list(flag_responses_map.keys()))
            )
            for flag in flag_records_to_update:
                flag.status = flag_responses_map[flag.value].status
                flag.response = flag_responses_map[flag.value].response

            Flag.bulk_update(
                flag_records_to_update, fields=[Flag.status, Flag.response]
            )

        logger.info("Done.")


if __name__ == "__main__":
    main()

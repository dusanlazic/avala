from shared.logs import logger
from apscheduler.schedulers.background import BlockingScheduler
from typing import Dict
from datetime import datetime
from ..models import Flag, FlagResponse
from ..config import load_user_config
from ..database import db, connect_database
from ..mq.rabbit import RabbitQueue, RabbitConnection, rabbit
from ..scheduler import get_tick_duration, get_next_tick_start


def main():
    load_user_config()
    connect_database()

    worker = Persister()
    worker.start()


class Persister:
    def __init__(self) -> None:
        self.scheduler: BlockingScheduler | None = None
        self._initialize()

    def start(self):
        self.scheduler.start()

    def _initialize(self):
        """Initializes and configures threads, consumers and scheduled jobs for flag response persistence based on the configuration."""
        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(
            func=self._persist_responses_in_batches_job,
            trigger="interval",
            seconds=5,
            id="persister",
        )

    def _persist_responses_in_batches_job(self):
        connection = RabbitConnection()
        connection.connect()

        persisting_buffer = []
        delivery_tag = None

        while True:
            method_frame, header_frame, body = connection.channel.basic_get(
                "persisting_queue"
            )
            if method_frame:
                flag_response = FlagResponse.from_json(body.decode())

                persisting_buffer.append(flag_response)
                delivery_tag = method_frame.delivery_tag
            else:
                logger.info(
                    "Pulled %d flags from the submission queue."
                    % len(persisting_buffer)
                )
                break

        self._persist_responses(
            persisting_buffer,
            delivery_tag,
            connection.channel,
        )

        connection.close()

    def _persist_responses(
        self,
        persisting_buffer: list[FlagResponse],
        delivery_tag: int,
        channel,
    ):
        """Persists responses from the persistence buffer into the database."""
        if not persisting_buffer:
            logger.info("No flag responses in buffer. Persistence skipped.")
            return

        logger.info("Persisting %d flag responses..." % len(persisting_buffer))

        flag_responses_map = {fr.value: fr for fr in persisting_buffer}

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

        channel.basic_ack(delivery_tag, multiple=True)
        logger.info("Done.")


if __name__ == "__main__":
    main()

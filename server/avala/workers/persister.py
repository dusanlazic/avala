from itertools import islice
from sqlalchemy.orm import Session
from apscheduler.schedulers.blocking import BlockingScheduler
from ..shared.logs import logger
from ..models import Flag, FlagResponse
from ..config import load_user_config
from ..database import get_db_context
from ..mq.rabbit import RabbitConnection

BATCH_SIZE = 1000
INTERVAL = 5


def main():
    load_user_config()

    with get_db_context() as db:
        worker = Persister(db)
        worker.start()


def batched(iterable, n):
    if n < 1:
        raise ValueError("n must be at least one")
    iterator = iter(iterable)
    while batch := tuple(islice(iterator, n)):
        yield batch


class Persister:
    def __init__(self, db: Session) -> None:
        self.scheduler: BlockingScheduler | None = None
        self.db = db
        self._initialize()

    def start(self):
        self.scheduler.start()

    def _initialize(self):
        """Initializes and configures threads, consumers and scheduled jobs for flag response persistence based on the configuration."""
        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(
            func=self._persist_responses_in_batches_job,
            trigger="interval",
            seconds=INTERVAL,
            id="persister",
        )

    def _persist_responses_in_batches_job(self):
        connection = RabbitConnection()
        connection.connect()

        while True:
            persisting_buffer = []
            delivery_tag_map = {}
            while len(persisting_buffer) < BATCH_SIZE:
                method, properties, body = connection.channel.basic_get(
                    "persisting_queue"
                )
                if method is None:
                    if persisting_buffer:
                        logger.info(
                            "Pulled all remaining %d responses from the persisting queue."
                            % len(persisting_buffer)
                        )
                    else:
                        logger.info(
                            "No flags remaining in the persisting queue. Persistence skipped."
                        )
                    break

                fr = FlagResponse.from_json(body.decode())
                persisting_buffer.append(fr)
                delivery_tag_map[fr.value] = method.delivery_tag

                if len(persisting_buffer) == BATCH_SIZE:
                    logger.info(
                        "Batch size reached. Pulled %d responses from the persisting queue."
                        % len(persisting_buffer)
                    )
                    break

            if not persisting_buffer:
                break

            self._persist_responses(
                persisting_buffer,
                delivery_tag_map,
                connection.channel,
            )

        connection.close()

    def _persist_responses(
        self,
        persisting_buffer: list[FlagResponse],
        delivery_tag_map: dict[str, int],
        channel,
    ):
        """Persists responses from the persistence buffer into the database."""
        if not persisting_buffer:
            logger.info("No flag responses in buffer. Persistence skipped.")
            return

        logger.info("Persisting %d flag responses..." % len(persisting_buffer))

        flag_responses_map = {fr.value: fr for fr in persisting_buffer}

        with self.db.begin():
            flag_records_to_update = (
                self.db.query(Flag)
                .filter(Flag.value.in_(list(flag_responses_map.keys())))
                .all()
            )

            updates = []
            for flag in flag_records_to_update:
                updates.append(
                    {
                        "id": flag.id,
                        "status": flag_responses_map[flag.value].status,
                        "response": flag_responses_map[flag.value].response,
                    }
                )

            self.db.bulk_update_mappings(Flag, updates)
            self.db.commit()
            updated_count = len(updates)

            logger.info("Updated %d records." % updated_count)

        channel.basic_ack(max(delivery_tag_map.values()), multiple=True)


if __name__ == "__main__":
    main()

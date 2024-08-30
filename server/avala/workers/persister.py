from itertools import islice
from sqlalchemy.orm import Session
from apscheduler.schedulers.blocking import BlockingScheduler
from ..shared.logs import logger
from ..models import Flag
from ..schemas import FlagSubmissionResponse
from ..database import get_db_context
from ..mq.rabbit import RabbitConnection, RabbitQueue

# TODO: Make configurable
BATCH_SIZE = 1000
INTERVAL = 5


def main():
    with get_db_context() as db:
        worker = Persister(db)
        worker.start()


class Persister:
    def __init__(self, db: Session) -> None:
        self.scheduler: BlockingScheduler | None = None
        self.db = db
        self._initialize()

    def start(self):
        self.scheduler.start()

    def _initialize(self):
        """
        Initializes and configures threads, consumers and scheduled jobs for flag response persistence based on the configuration.
        """
        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(
            func=self._persist_responses_in_batches_job,
            trigger="interval",
            seconds=INTERVAL,
            id="persister",
        )

    def _persist_responses_in_batches_job(self):
        with RabbitConnection(silent=True) as connection:
            persisting_queue = RabbitQueue(
                connection.channel,
                "persisting_queue",
                durable=True,
                silent=True,
            )

            while True:
                persisting_buffer: list[FlagSubmissionResponse] = []
                delivery_tag_map: dict[str, int] = {}

                while len(persisting_buffer) < BATCH_SIZE:
                    method, properties, body = persisting_queue.get()
                    if method is None:
                        if persisting_buffer:
                            logger.info(
                                "Pulled all remaining {count} responses from the persisting queue.",
                                count=len(persisting_buffer),
                            )
                        else:
                            logger.info(
                                "No flags remaining in the persisting queue. Persistence skipped."
                            )
                        break

                    fr = FlagSubmissionResponse.model_validate_json(body)
                    persisting_buffer.append(fr)
                    delivery_tag_map[fr.value] = method.delivery_tag

                    if len(persisting_buffer) == BATCH_SIZE:
                        logger.info(
                            "Batch size reached. Pulled {count} responses from the persisting queue.",
                            count=len(persisting_buffer),
                        )
                        break

                if not persisting_buffer:
                    break

                self._persist_responses(
                    persisting_buffer,
                    delivery_tag_map,
                    connection,
                )

    def _persist_responses(
        self,
        persisting_buffer: list[FlagSubmissionResponse],
        delivery_tag_map: dict[str, int],
        connection: RabbitConnection,
    ):
        """
        Persists responses from the persistence buffer into the database.
        """
        if not persisting_buffer:
            logger.info("No flag responses in buffer. Persistence skipped.")
            return

        logger.info(
            "Persisting {count} flag responses...", count=len(persisting_buffer)
        )

        flag_responses_map = {fr.value: fr for fr in persisting_buffer}

        with self.db.begin():
            flag_records_to_update = (
                self.db.query(Flag)
                .filter(Flag.value.in_(list(flag_responses_map.keys())))
                .all()
            )

            updates = []
            for flag in flag_records_to_update:
                flag_response = flag_responses_map[flag.value]
                updates.append(
                    {
                        "id": flag.id,
                        "status": flag_response.status,
                        "response": flag_response.response,
                    }
                )

            self.db.bulk_update_mappings(Flag, updates)
            updated_count = len(updates)

            logger.info("Updated {count} records.", count=updated_count)

        connection.ack(max(delivery_tag_map.values()), multiple=True)


if __name__ == "__main__":
    main()

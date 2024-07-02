import os
import sys
from addict import Dict
from itertools import islice
from shared.logs import logger
from apscheduler.schedulers.background import BlockingScheduler
from datetime import datetime, timedelta
from collections import Counter
from importlib import import_module, reload
from ..models import FlagResponse
from ..config import load_user_config, config
from ..mq.rabbit import RabbitQueue, RabbitConnection
from ..scheduler import (
    get_tick_elapsed,
    get_tick_duration,
    get_next_tick_start,
    get_first_tick_start,
    game_has_started,
)


def main():
    load_user_config()

    if config.submitter.max_batch_size < 1:
        config.submitter.max_batch_size = float("inf")

    worker = Submitter()
    worker.start()


def batched(iterable, n):
    if n < 1:
        raise ValueError("n must be at least one")
    iterator = iter(iterable)
    while batch := tuple(islice(iterator, n)):
        yield batch


class Submitter:
    def __init__(self) -> None:
        self.scheduler: BlockingScheduler | None = None
        self.connection: RabbitConnection | None = None

        self.submission_buffer: list[str] | None = None
        self.delivery_tag_map: dict[str, int] | None = None

        self.submission_queue: RabbitQueue | None = None
        self.persisting_queue: RabbitQueue | None = None

        self.submit = self._import_submit_function()
        self._initialize()

    def start(self):
        if config.submitter.per_tick or config.submitter.interval:
            self.scheduler.start()
        elif config.submitter.batch_size:
            self.connection.channel.start_consuming()
        elif config.submitter.streams:
            pass

    def _initialize(self):
        """Initializes threads, consumers and scheduled jobs for flag submission based on the configuration.

        Configuration options:

            submitter.per_tick:
                Number of submissions per tick. If set, submissions are spread across the tick duration.

            submitter.interval:
                Interval in seconds between submissions. Used when flags are submitted at fixed intervals.

            submitter.batch_size:
                Size of each batch for flag submission. Submissions trigger when queue reaches batch size.

            submitter.streams:
                Number of continuous streams (threads) for flag submission.

        The function sets up different submission strategies based on the provided configuration. It automatically
        calculates the next run time for each submission job to synchronize with game ticks.
        """

        if config.submitter.per_tick or config.submitter.interval:
            interval, next_run_time = self._calculate_next_run_time()

            self.scheduler = BlockingScheduler()
            self.scheduler.add_job(
                func=self._submit_flags_scheduled_job,
                trigger="interval",
                seconds=interval.total_seconds(),
                id="submitter",
                next_run_time=next_run_time,
            )
        elif config.submitter.batch_size:
            self.submission_buffer = []
            self.delivery_tag_map = {}

            self.connection = RabbitConnection()
            self.connection.connect()

            self.submission_queue = RabbitQueue(
                self.connection.channel, "submission_queue", durable=True
            )
            self.persisting_queue = RabbitQueue(
                self.connection.channel, "persisting_queue", durable=True
            )

            self.submission_queue.add_consumer(self._submit_flags_in_batches_consumer)
        elif config.submitter.streams:
            self.submission_queue.add_consumer(self._submit_flags_in_stream_consumer)

    def _submit_flags_in_batches_consumer(self, ch, method, properties, body):
        """TODO docstring"""
        flag = body.decode().strip()

        self.submission_buffer.append(flag)
        self.delivery_tag_map[flag] = method.delivery_tag

        logger.debug(
            "Received flag <bold>%s</bold> (%d flags in buffer)"
            % (flag, len(self.submission_buffer))
        )

        if len(self.submission_buffer) < config.submitter.batch_size:
            return  # Skip submission if batch size not reached

        self._submit_flags(
            self.submission_buffer,
            self.delivery_tag_map,
            self.persisting_queue,
            self.connection.channel,
        )

        self.submission_buffer.clear()
        self.delivery_tag_map.clear()

    def _submit_flags_scheduled_job(self):
        """TODO docstring"""
        connection = RabbitConnection()
        connection.connect()

        persisting_queue = RabbitQueue(
            connection.channel, "persisting_queue", durable=True
        )

        while True:
            submission_buffer = []
            delivery_tag_map = {}
            while len(submission_buffer) < config.submitter.max_batch_size:
                method, properties, body = connection.channel.basic_get(
                    "submission_queue"
                )
                if method is None:
                    if submission_buffer:
                        logger.info(
                            "Pulled all remaining %d flags from the submission queue."
                            % len(submission_buffer)
                        )
                    else:
                        logger.info(
                            "No flags remaining in the submission queue. Submission skipped."
                        )
                    break

                flag = body.decode().strip()
                submission_buffer.append(flag)
                delivery_tag_map[flag] = method.delivery_tag

                if len(submission_buffer) == config.submitter.max_batch_size:
                    logger.info(
                        "Batch size reached. Pulled %d flags from the submission queue."
                        % len(submission_buffer)
                    )
                    break

            if not submission_buffer:
                break

            self._submit_flags(
                submission_buffer,
                delivery_tag_map,
                persisting_queue,
                connection.channel,
            )

        connection.close()

    def _submit_flags(
        self,
        submission_buffer: list[str],
        delivery_tag_map: dict[str, int],
        persisting_queue: RabbitQueue,
        channel,
    ):
        """Submits flags from the submission buffer."""
        if not submission_buffer:
            logger.info("No flags in buffer. Submission skipped.")
            return

        logger.info("Submitting <bold>%d</bold> flags..." % len(submission_buffer))

        flag_responses = [
            FlagResponse(*response) for response in self.submit(submission_buffer)
        ]

        for fr in flag_responses:
            channel.basic_ack(delivery_tag_map[fr.value])
            persisting_queue.put(fr.to_json())

        stats = Counter(fr.status for fr in flag_responses)
        logger.info(
            "<green>%d accepted</green> - <red>%d rejected</red>"
            % (
                stats["accepted"],
                stats["rejected"],
            )
        )

    def _submit_flags_in_stream_consumer(self, ch, method, properties, body):
        flag = body.decode().strip()
        logger.debug("Received flag <bold>%s</bold>" % flag)

        response = FlagResponse(*self.submit(flag))
        ch.ack(delivery_tag=method.delivery_tag)

        logger.debug(
            "<green>Accepted</green> %s" % response.response
            if response.status == "accepted"
            else "<red>Rejected</red> %s" % response.response
        )

        self.persisting_queue.put(response.to_json())

    def _import_submit_function(self):
        """Imports and reloads the submit function that does the actual flag submission."""
        module_name = (
            config.submitter.module if config.submitter.module else "submitter"
        )

        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.append(cwd)

        imported_module = reload(import_module(module_name))
        submit_function = getattr(imported_module, "submit")

        return submit_function

    def _calculate_next_run_time(self) -> tuple[timedelta, datetime]:
        now = datetime.now()
        tick_duration = get_tick_duration()
        next_tick_start = get_next_tick_start(now)

        submissions_per_tick = config.submitter.per_tick

        if submissions_per_tick:
            interval: timedelta = tick_duration / (submissions_per_tick - 1)
        else:
            interval: timedelta = timedelta(seconds=config.submitter.interval)

        if game_has_started():
            tick_elapsed = get_tick_elapsed(now)

            next_run_time = (
                next_tick_start
                - tick_duration
                + (tick_elapsed // interval + 1) * interval
            )
        else:
            next_run_time = get_first_tick_start() + interval

        return interval, next_run_time


if __name__ == "__main__":
    main()

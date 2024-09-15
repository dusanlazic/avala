import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from importlib import import_module, reload

from apscheduler.schedulers.blocking import BlockingScheduler

from ..broadcast import emitter
from ..config import get_config
from ..mq.rabbit import RabbitConnection, RabbitQueue
from ..scheduler import (
    game_has_started,
    get_next_tick_start,
    get_tick_elapsed,
)
from ..schemas import FlagCounterDelta, FlagSubmissionResponse
from ..shared.logs import logger

config = get_config()


def main():
    emitter.connect()
    worker = Submitter()
    worker.start()


class Submitter:
    def __init__(self) -> None:
        self.scheduler: BlockingScheduler
        self.connection: RabbitConnection

        self.submission_buffer: list[str]
        self.delivery_tag_map: dict[str, int]

        self.submission_queue: RabbitQueue
        self.persisting_queue: RabbitQueue

        self.ready = False
        self._initialize()

    def _initialize(self):
        """
        TODO: Docstrings
        """
        try:
            self.submit = self._import_user_function("submit")
        except Exception as e:
            logger.error(
                "Unable to load module <b>{module}</>: {error}",
                module=config.submitter.module,
                error=e,
            )
            return

        if self.submit is None:
            logger.error(
                "Required function not found within <b>{module}.py</>. Please make sure the module contains <b>submit</> function.",
                module=config.submitter.module,
            )
            return

        self.prepare = self._import_user_function("prepare")
        self.cleanup = self._import_user_function("cleanup")

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
            try:
                self.connection.connect()
            except Exception as e:
                logger.error(
                    "Failed to connect to RabbitMQ: {error}",
                    error=e,
                )
                return

            self.submission_queue = RabbitQueue(
                self.connection.channel, "submission_queue", durable=True
            )
            self.persisting_queue = RabbitQueue(
                self.connection.channel, "persisting_queue", durable=True
            )

            self.submission_queue.add_consumer(self._submit_flags_in_batches_consumer)
        elif config.submitter.streams:
            self.connection = RabbitConnection()
            try:
                self.connection.connect()
            except Exception as e:
                logger.error(
                    "Failed to connect to RabbitMQ: {error}",
                    error=e,
                )
                return

            self.submission_queue = RabbitQueue(
                self.connection.channel, "submission_queue", durable=True
            )
            self.persisting_queue = RabbitQueue(
                self.connection.channel, "persisting_queue", durable=True
            )

            self.submission_queue.add_consumer(self._submit_flags_in_stream_consumer)

        self.ready = True

    def start(self):
        if not self.ready:
            return
        if config.submitter.per_tick or config.submitter.interval:
            self.scheduler.start()
        elif config.submitter.batch_size:
            self.connection.start_consuming()
        elif config.submitter.streams:
            if self.prepare:
                self.prepare()
            self.connection.start_consuming()
            if self.cleanup:
                self.cleanup()

    def _submit_flags_in_batches_consumer(self, ch, method, properties, body):
        """TODO docstring"""
        flag = body.decode().strip()

        self.submission_buffer.append(flag)
        self.delivery_tag_map[flag] = method.delivery_tag

        logger.debug(
            "Received flag <b>{flag}</> ({count} flags in buffer)",
            flag=flag,
            count=len(self.submission_buffer),
        )

        if len(self.submission_buffer) < config.submitter.batch_size:
            return  # Skip submission if batch size not reached

        self._submit_flags_from_buffer(
            self.submission_buffer,
            self.delivery_tag_map,
            self.persisting_queue,
            self.connection,
        )

        self.submission_buffer.clear()
        self.delivery_tag_map.clear()

    def _submit_flags_scheduled_job(self):
        try:
            connection = RabbitConnection(silent=True)
            with connection:
                submission_queue = RabbitQueue(
                    connection.channel,
                    "submission_queue",
                    durable=True,
                    silent=True,
                )

                persisting_queue = RabbitQueue(
                    connection.channel,
                    "persisting_queue",
                    durable=True,
                    silent=True,
                )

                while True:
                    submission_buffer = []
                    delivery_tag_map = {}
                    while len(submission_buffer) < config.submitter.max_batch_size:
                        method, properties, body = submission_queue.get()
                        if method is None:
                            if submission_buffer:
                                logger.info(
                                    "Pulled all remaining {count} flags from the submission queue.",
                                    count=len(submission_buffer),
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
                                "Batch size reached. Pulled {count} flags from the submission queue.",
                                count=len(submission_buffer),
                            )
                            break

                    if not submission_buffer:
                        break

                    self._submit_flags_from_buffer(
                        submission_buffer,
                        delivery_tag_map,
                        persisting_queue,
                        connection,
                    )
        except Exception as e:
            logger.error(
                "Failed to connect to RabbitMQ: {error}",
                error=e,
            )

    def _submit_flags_from_buffer(
        self,
        submission_buffer: list[str],
        delivery_tag_map: dict[str, int],
        persisting_queue: RabbitQueue,
        connection: RabbitConnection,
    ):
        """
        Submits flags from the submission buffer.
        """
        if not submission_buffer:
            logger.info("No flags in buffer. Submission skipped.")
            return

        logger.info("Submitting <b>{count}</> flags...", count=len(submission_buffer))

        response_statuses: list[str] = []
        dropped_flags: set[str] = set(submission_buffer)

        for response_tuple in self.submit(submission_buffer):
            response = FlagSubmissionResponse.from_tuple(response_tuple)
            if response.status != "requeued":
                connection.ack(delivery_tag_map[response.value])
                persisting_queue.put(response.model_dump_json())
                dropped_flags.discard(response.value)

            response_statuses.append(response.status)

        for flag in dropped_flags:
            connection.reject(delivery_tag_map[flag], requeue=True)

        stats = Counter(response_statuses)
        logger.info(
            "<green>{accepted} accepted</green>, <red>{rejected} rejected</red>, <blue>{requeued} requeued</blue>",
            accepted=stats["accepted"],
            rejected=stats["rejected"],
            requeued=stats["requeued"],
        )

        emitter.emit(
            "flags",
            FlagCounterDelta(
                queued=(stats["accepted"] + stats["rejected"]) * -1,
                discarded=0,
                accepted=stats["accepted"],
                rejected=stats["rejected"],
            ).model_dump_json(exclude_unset=True),
        )

    def _submit_flag_or_exit(self, flag: str):
        attempts = 10
        while attempts:
            try:
                return self.submit(flag)
            except:
                attempts -= 1
                if self.cleanup:
                    self.cleanup()
                if self.prepare:
                    self.prepare()

        logger.error(
            "Failed to submit flag <b>{flag}</>. Check your connection and rerun.",
            flag=flag,
        )
        exit(1)

    def _submit_flags_in_stream_consumer(self, ch, method, properties, body):
        flag = body.decode().strip()
        logger.debug("Received flag <b>{flag}</>", flag=flag)

        response_tuple = self._submit_flag_or_exit(flag)
        if not response_tuple:
            logger.debug("<blue>Requeued</blue> {flag}", flag=flag)
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
            return

        response = FlagSubmissionResponse.from_tuple(response_tuple)
        if response.status != "requeued":
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.persisting_queue.put(response.model_dump_json())
            logger.debug(
                (
                    "<green>Accepted</green> {response}"
                    if response.status == "accepted"
                    else "<red>Rejected</red> {response}"
                ),
                response=response.response,
            )

            emitter.emit(
                "flags",
                FlagCounterDelta(
                    queued=-1,
                    discarded=0,
                    accepted=1 if response.status == "accepted" else 0,
                    rejected=1 if response.status == "rejected" else 0,
                ).model_dump_json(exclude_unset=True),
            )
        else:
            logger.debug("<blue>Requeued</blue> {response}", response=response.response)
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)

    def _import_user_function(self, function_name: str):
        """Imports and reloads user written functions used for the actual flag submission."""
        module_name = (
            config.submitter.module if config.submitter.module else "submitter"
        )

        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.append(cwd)

        imported_module = reload(import_module(module_name))
        return getattr(imported_module, function_name, None)

    def _calculate_next_run_time(self) -> tuple[timedelta, datetime]:
        now = datetime.now()
        tick_duration = config.game.tick_duration
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
            next_run_time = config.game.game_starts_at + interval

        return interval, next_run_time


if __name__ == "__main__":
    main()

import os
import sys
import pika
import json
from shared.logs import logger
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread
from typing import Dict
from datetime import datetime, timedelta
from collections import namedtuple, Counter
from importlib import import_module, reload
from .models import Flag
from .config import config
from .database import db
from .scheduler import (
    get_tick_elapsed,
    get_tick_duration,
    get_next_tick_start,
    get_first_tick_start,
    game_has_started,
)


class FlagResponse(namedtuple("FlagResponse", "value status response")):
    def serialize(self):
        return json.dumps(self._asdict())

    def deserialize(response):
        return FlagResponse(**json.loads(response))


class RabbitMQQueue:
    """A simple wrapper around a RabbitMQ queue."""

    def __init__(self, channel, routing_key) -> None:
        self.channel = channel
        self.routing_key = routing_key

        self.latest_delivery_tag = None
        self.channel.queue_declare(queue=self.routing_key, durable=True)

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


class SubmissionHandler:
    def __init__(self, scheduler: BackgroundScheduler) -> None:
        self.channel = self._initialize_rabbitmq()

        self.submit = self._import_submit_function()

        self.submission_buffer: list[str] = []
        self.submission_delivery_tags: list[int] = []
        self.submission_queue = RabbitMQQueue(self.channel, "submission_queue")

        self.persisting_buffer: list[FlagResponse] = []
        self.persisting_delivery_tags: list[int] = []
        self.persisting_queue = RabbitMQQueue(self.channel, "persisting_queue")

        self.persisting_queue.add_consumer(self._persist_responses_in_batches_consumer)

        self._initialize_submitter(scheduler)

    def _initialize_submitter(self):
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

        Args:
            scheduler (BackgroundScheduler): The scheduler used for managing submission jobs.

        The function sets up different submission strategies based on the provided configuration. It automatically
        calculates the next run time for each submission job to synchronize with game ticks.
        """
        now = datetime.now()
        tick_duration = get_tick_duration()
        next_tick_start = get_next_tick_start(now)

        if config.submitter.per_tick or config.submitter.interval:
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

            self.scheduler.add_job(
                func=self._submit_flags_scheduled_job,
                trigger="interval",
                seconds=interval.total_seconds(),
                id="submitter",
                next_run_time=next_run_time,
            )
        elif config.submitter.batch_size:
            self.submission_queue.add_consumer(self._submit_flags_in_batches_consumer)

            self.scheduler.add_job(
                func=self._submit_flags_scheduled_job,
                trigger="interval",
                seconds=tick_duration.total_seconds(),
                id="submitter",
                next_run_time=next_tick_start,
            )
        elif config.submitter.streams:
            threads = config.submitter.streams
            submit = self._import_submit_function()
            for num in range(threads):
                Thread(target=self._submit_flags_stream_job, args=(submit, num)).start()

    def _initialize_rabbitmq(self):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=config.rabbitmq.host,
                port=config.rabbitmq.port,
                credentials=pika.PlainCredentials(
                    config.rabbitmq.username, config.rabbitmq.password
                ),
            )
        )

        channel = connection.channel()
        channel.queue_declare(queue="submission_queue", durable=True)
        channel.queue_declare(queue="persisting_queue", durable=True)

        return channel

    def _submit_flags_in_batches_consumer(self, ch, method, properties, body):
        """Receives flags from the submission queue and initiates submission of a batch of queued flags.

        The function retrieves flags from the submission queue, loads them into the submission buffer,
        and initiates their submission when the buffer reaches the configured batch size. After submission,
        it acknowledges the messages and moves the responses to the persisting queue.
        """
        self.submission_buffer.append(body.decode())
        if len(self.submission_buffer) >= config.submitter.batch_size:
            flag_repsonses = self._submit_flags()
            ch.basic_ack(delivery_tag=method.delivery_tag, multiple=True)
            self.submission_buffer.clear()

            for fr in flag_repsonses:
                self.persisting_queue.put(fr.serialize())

    def _submit_flags_in_intervals_consumer(self, ch, method, properties, body):
        """Receives flags from the submission queue and moves them straight to the submission buffer.

        It is used when the submitter is configured to run at fixed intervals or fixed number of times
        per tick. The function moves flags straight to the submission buffer making them ready to be
        submitted. It also tracks delivery tags for acknowledging the messages later.
        """
        self.submission_buffer.append(body.decode())
        self.submission_delivery_tags.append(method.delivery_tag)

    def _submit_flags_in_stream_consumer(self, ch, method, properties, body):
        flag = body.decode().strip()
        response = FlagResponse(*self.submit(flag))
        ch.ack(delivery_tag=method.delivery_tag)
        self.persisting_queue.put(response.serialize())

    def _submit_flags_scheduled_job(self):
        """Initiates submission of all flags from the submission buffer.

        The function is used when the submitter is configured to run at fixed intervals or fixed number of
        times per tick. It is called by the scheduler at fixed intervals. After submission, it acknowledges
        the messages and moves the responses to the persisting queue.
        """
        flag_responses = self._submit_flags()
        if not flag_responses:
            return

        delivery_tag = max(self.submission_delivery_tags)
        self.submission_queue.ack(delivery_tag=delivery_tag, multiple=True)
        self.submission_buffer.clear()
        self.submission_delivery_tags.clear()

        for fr in flag_responses:
            self.persisting_queue.put(fr.serialize())

    def _submit_flags(self) -> list[FlagResponse]:
        """Submits flags from the submission buffer.

        The function reloads the submitter function and submits flags from the submission buffer.
        This function is called when flag submission is triggered at fixed intervals by the scheduler
        or when there are enough flags for submitting a batch, depending on the configuration.
        """
        if not self.submission_buffer:
            logger.info("No flags in buffer. Submission skipped.")
            return []

        logger.info(
            "Submitting <bold>%d/%d</bold> flags..."
            % (
                len(self.submission_buffer),
                len(self.submission_buffer) + self.submission_queue.size(),
            )
        )

        flag_responses = [
            FlagResponse(*response) for response in self.submit(self.submission_buffer)
        ]

        stats = Counter(fr.status for fr in flag_responses)
        logger.info(
            "<green>%d accepted</green> - <red>%d rejected</red> - <cyan>%d queued</cyan>"
            % (stats["accepted"], stats["rejected"], self.submission_queue.size())
        )

        return flag_responses

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

    def _import_submit_function(self):
        """Imports and reloads the submit function that does the actual flag submission."""
        module_name = config.submitter.module

        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.append(cwd)

        imported_module = reload(import_module(module_name))
        submit_function = getattr(imported_module, "submit")

        return submit_function

    def _get_log_debug_function(self, thread_num):
        def debug(message):
            logger.debug(
                "<light-blue>submit:%d</light-blue> -> %s" % (thread_num, message)
            )

        return debug

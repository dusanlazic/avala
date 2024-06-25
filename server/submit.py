import os
import sys
import threading
from shared.logs import logger
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Dict
from datetime import datetime, timedelta
from collections import namedtuple, Counter
from queue import Queue
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


FlagResponse = namedtuple("FlagResponse", "value status response")


submission_queue: Queue[str] = Queue()
persisting_queue: Queue[FlagResponse] = Queue()

submission_buffer: list[str] = []
persisting_buffer: list[FlagResponse] = []


def initialize_submitter(scheduler: BackgroundScheduler):
    """Initializes threads and schedules jobs for flag submission based on the configuration.

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

    The function sets up different submission strategies based on the provided configuration. It automatically calculates
    the next run time for each submission job to synchronize with game ticks.
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

        scheduler.add_job(
            func=submit_flags_from_queue,
            trigger="interval",
            seconds=interval.total_seconds(),
            id="submitter",
            next_run_time=next_run_time,
        )
    elif config.submitter.batch_size:
        threading.Thread(target=submit_flags_in_batches_job).start()

        scheduler.add_job(
            func=submit_flags_from_queue,
            trigger="interval",
            seconds=tick_duration.total_seconds(),
            id="submitter",
            next_run_time=next_tick_start,
        )
    elif config.submitter.streams:
        threads = config.submitter.streams
        submit = import_submit_function()
        for num in range(threads):
            threading.Thread(target=submit_flags_stream_job, args=(submit, num)).start()

    threading.Thread(target=persist_flags_in_batches_job).start()


def submit_flags_stream_job(submit, num):
    """Starts a continuous flag submission stream in a separate thread."""
    logger.info("Starting submitter stream in thread %s..." % num)
    debug_func = get_log_debug_function(num)
    submit(submission_queue, persisting_queue, debug_func)


def submit_flags_from_queue():
    """Initiates submission of all queued flags.

    The function retrieves all flags from the submission queue, loads them into the submission buffer,
    and initiates their submission. It is called when the submitter is configured to run at fixed
    intervals, or fixed number of times per tick.
    """
    while not submission_queue.empty():
        submission_buffer.append(submission_queue.get())
    submit_flags_from_buffer()


def submit_flags_in_batches_job():
    """Initiates submission of a batch of queued flags.

    The function retrieves a fixed number of flags from the submission queue, loads them into the
    submission buffer, and initiates their submission. It is called when the submitter is configured
    to run in batches and the queue reaches the batch size.
    """
    while True:
        submission_buffer.append(submission_queue.get())
        if len(submission_buffer) >= config.submitter.batch_size:
            submit_flags_from_buffer()


def submit_flags_from_buffer():
    """
    This function reimports the submitter function, submits flags from the submission buffer,
    and then puts the responses into the persisting queue.

    This function is called when flag submission is triggered by the scheduler or when there
    are enough flags for submitting a batch, depending on the configuration.
    """
    if not submission_buffer:
        logger.info("No flags in queue. Submission skipped.")
        return

    logger.info(
        "Submitting <bold>%d/%d</bold> flags..."
        % (len(submission_buffer), len(submission_buffer) + submission_queue.qsize())
    )

    submit = import_submit_function()
    flag_responses = [FlagResponse(*response) for response in submit(submission_buffer)]

    stats = Counter(fr.status for fr in flag_responses)
    logger.info(
        "<green>%d accepted</green> - <red>%d rejected</red> - <cyan>%d queued</cyan>"
        % (stats["accepted"], stats["rejected"], submission_queue.qsize())
    )

    for fr in flag_responses:
        persisting_queue.put(fr)

    submission_buffer.clear()


def persist_flags_in_batches_job(batch_size=50):
    """
    This function loads a fixed amount of flag responses into the persisting buffer,
    and then starts the flag response persistence process.

    This function is meant to be constantly running in a separate thread.
    """
    while True:
        persisting_buffer.append(persisting_queue.get())
        if len(persisting_buffer) >= batch_size:
            persist_flags_from_buffer()


def persist_flags_from_buffer():
    """
    This function persists flags from the submission buffer into the database.
    """
    flag_responses_map: Dict[str, FlagResponse] = {}

    for flag_response in persisting_buffer:
        flag_responses_map[flag_response.value] = flag_response

    with db.atomic():
        flag_records_to_update = Flag.select().where(
            Flag.value.in_(list(flag_responses_map.keys()))
        )
        for flag in flag_records_to_update:
            flag.status = flag_responses_map[flag.value].status
            flag.response = flag_responses_map[flag.value].response

        Flag.bulk_update(flag_records_to_update, fields=[Flag.status, Flag.response])

    persisting_buffer.clear()


def import_submit_function():
    """
    This function imports the submit function that does the actual flag submission.
    """
    module_name = config.submitter.module

    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.append(cwd)

    imported_module = reload(import_module(module_name))
    submit_function = getattr(imported_module, "submit")

    return submit_function


def get_log_debug_function(thread_num):
    def debug(message):
        logger.debug("<light-blue>submit:%d</light-blue> -> %s" % (thread_num, message))

    return debug

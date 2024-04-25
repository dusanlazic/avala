import threading
from typing import Dict
from datetime import datetime, timedelta
from collections import namedtuple
from queue import Queue
from importlib import import_module, reload
from .models import Flag
from .config import config
from .database import db
from .scheduler import (
    scheduler,
    get_tick_duration,
    get_next_tick_start,
    get_tick_elapsed,
)


FlagResponse = namedtuple("FlagResponse", "value status response")


submission_queue: Queue[str] = Queue()
persisting_queue: Queue[FlagResponse] = Queue()

submission_buffer: list[str] = []
persisting_buffer: list[FlagResponse] = []


def initialize_submitter():
    if config["submitter"].get("per_tick"):
        submissions_per_tick = config["submitter"]["per_tick"]
        tick_duration = get_tick_duration()
        interval: timedelta = tick_duration / (submissions_per_tick - 1)

        now = datetime.now()
        next_run_time = (
            get_next_tick_start(now)
            - tick_duration
            + (get_tick_elapsed(now) // interval + 1) * interval
        )

        scheduler.add_job(
            func=submit_flags_from_queue,
            trigger="interval",
            seconds=interval.seconds,
            id="submitter",
            next_run_time=next_run_time,
        )
    elif config["submitter"].get("batch_size"):
        size = config["submitter"]["batch_size"]
        threading.Thread(target=submit_flags_in_batches_job, args=(size,)).start()
    elif config["submitter"].get("streams"):
        threads = config["submitter"]["streams"]
        submit = import_submit_function()
        for _ in range(threads):
            threading.Thread(target=submit_flags_stream_job, args=(submit,)).start()

    threading.Thread(target=persist_flags_in_batches_job).start()


def submit_flags_stream_job(submit):
    # Support error recovery and stuff here
    submit(submission_queue, persisting_queue)


def submit_flags_from_queue():
    while not submission_queue.empty():
        submission_buffer.append(submission_queue.get())
    submit_flags_from_buffer()


def submit_flags_in_batches_job(batch_size=50):
    while True:
        submission_buffer.append(submission_queue.get())
        if len(submission_buffer) >= batch_size:
            submit_flags_from_buffer()


def submit_flags_from_buffer():
    submit = import_submit_function()
    map(
        persisting_queue.put,
        [FlagResponse(*response) for response in submit(submission_buffer)],
    )

    submission_buffer.clear()


def persist_flags_in_batches_job(batch_size=50):
    while True:
        persisting_buffer.append(persisting_queue.get())
        if len(persisting_buffer) >= batch_size:
            persist_flags_from_buffer()


def persist_flags_from_buffer():
    flag_responses_map: Dict[str, FlagResponse] = {}

    for flag_response in persisting_buffer:
        flag_responses_map[flag_response.value] = flag_response

    with db.atomic():
        flag_records_to_update = Flag.select().where(
            Flag.value.in_(flag_responses_map.keys())
        )
        for flag in flag_records_to_update:
            flag.status = flag_responses_map[flag.value].status
            flag.response = flag_responses_map[flag.value].response

        Flag.bulk_update(flag_records_to_update, fields=[Flag.status, Flag.response])

    persisting_buffer.clear()


def import_submit_function():
    module_name = config["submitter"]["module"]

    imported_module = reload(import_module(module_name))
    submit_function = getattr(imported_module, "submit")

    return submit_function


def run():
    # Queue can be clogged if there is to many flags to submit and submitting service is too slow!
    # If flag checking service is REST API, you should be able to limit how many flags per request.
    pass

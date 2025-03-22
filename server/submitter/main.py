import inspect
import os
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timedelta
from importlib import import_module, reload
from typing import Any, Callable, Literal, TypeAlias

import pika
import pika.adapters.blocking_connection
import pika.channel

from config import config
from logger import logger
from scheduler import game_has_started, get_tick_elapsed
from schemas import FlagPersistMessage

StreamSubmitFunction: TypeAlias = Callable[[str], tuple[Literal["accepted", "rejected", "requeued"], str]]
BatchSubmitFunction: TypeAlias = Callable[
    [list[str]], list[tuple[Literal["accepted", "rejected", "requeued"], str, str]]
]


def connect_to_rabbitmq():
    """
    Connects to RabbitMQ using the configuration settings and returns the connection and channel objects.
    If the connection fails, the program exits with an error message.
    """
    credentials = pika.PlainCredentials(config.rabbitmq.user, config.rabbitmq.password)
    parameters = pika.ConnectionParameters(
        host=config.rabbitmq.host,
        port=config.rabbitmq.port,
        credentials=credentials,
    )

    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        logger.success("Connected to RabbitMQ.")
        return connection, channel
    except Exception as e:
        logger.error(
            "Failed to connect to RabbitMQ. <b>{error}</>: {error_msg}",
            error=type(e).__name__,
            error_msg=e,
        )
        exit(1)


def determine_strategy() -> Literal["INTERVAL", "STREAM", "BATCH"]:
    """
    Determines the submission strategy based on the fields present in the submitter configuration.
    """
    field_strategy_map = {
        frozenset(["interval", "batch_size"]): "INTERVAL",
        frozenset(["per_tick", "batch_size"]): "INTERVAL",
        frozenset(["batch_size"]): "BATCH",
        frozenset(["workers"]): "STREAM",
    }
    allowed_fields = set().union(*field_strategy_map.keys())

    present_fields = frozenset(config.submitter.model_dump(exclude_none=True).keys() & allowed_fields)
    return field_strategy_map[present_fields]  # type: ignore


def import_user_function(func_name: str) -> Callable | None:
    """
    Dynamically imports a function written by the user from the submitter module.
    """
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.append(cwd)

    imported_module = reload(import_module(config.submitter.module))
    return getattr(imported_module, func_name, None)


def prepare_context() -> Any:
    """
    Imports and executes the user-definted setup function from the submitter module, if present.
    """
    setup_func = import_user_function("setup")
    return setup_func() if setup_func else None


def prepare_submit_function(submitter_context: Any) -> Callable:
    """
    Imports the user-defined submit function from the submitter module and fixes context argument
    if required by the function.
    """
    submit_func = import_user_function("submit")
    if not submit_func:
        logger.error("Submit function not found in user script.")
        exit(1)

    match len(inspect.signature(submit_func).parameters):
        case 1:
            return submit_func
        case 2:
            return lambda f: submit_func(f, submitter_context)  # noqa: E731
        case _:
            logger.error("Teardown function should not have more than two arguments.")
            exit(1)


def prepare_teardown_function(submitter_context: Any) -> Callable | None:
    """
    Imports the user-defined teardown function from the submitter module if exists, and fixes context argument
    if required by the function.
    """
    teardown_func = import_user_function("teardown")
    if not teardown_func:
        return None

    match len(inspect.signature(teardown_func).parameters):
        case 0:
            return teardown_func
        case 1:
            return lambda: teardown_func(submitter_context)  # noqa: E731
        case _:
            logger.error("Teardown function should not have more than one argument.")
            exit(1)


def calculate_next_submit_time() -> timedelta:
    """
    Calculates the time to wait before the next flag submission based on the current time and the submitter
    configuration.
    """
    now = datetime.now()

    interval: timedelta
    if config.submitter.interval:
        interval = config.submitter.interval
    elif config.submitter.per_tick:
        interval = config.game.tick_duration / config.submitter.per_tick

    if game_has_started(now):
        elapsed = get_tick_elapsed(now)
        return (elapsed // interval + 1) * interval - elapsed
    else:
        return (config.game.game_starts_at + interval) - now


def start_interval_consumer(channel, submit_flags: BatchSubmitFunction) -> None:  # noqa: C901
    """
    Starts a loop that pulls flags from the 'flag.submission' queue in fixed intervals and processes them
    using the user-defined submit function.
    """
    queue_cleared = True
    while True:
        if queue_cleared:
            sleep_for = calculate_next_submit_time().total_seconds()
            logger.info(
                "Next submission scheduled at <b>"
                + (datetime.now() + timedelta(seconds=sleep_for)).strftime("%H:%M:%S")
                + "</>."
            )
            time.sleep(sleep_for)
            queue_cleared = False

        flag_tag_map: dict[str, int] = {}
        flag_attempt_map: dict[str, int] = {}

        for _ in range(config.submitter.batch_size):  # type: ignore
            method_frame, header_frame, body = channel.basic_get(queue="flag.submission", auto_ack=False)

            if method_frame:
                tag: int = method_frame.delivery_tag
                flag: str = body.decode().strip()
                attempt: int = header_frame.headers.get("x-delivery-count", 0) if header_frame.headers else 0

                flag_tag_map[flag] = tag
                flag_attempt_map[flag] = attempt
            else:
                queue_cleared = True
                break

        if not flag_tag_map:
            logger.info("No flags to submit.")
            continue

        logger.info("Submitting <b>{count}</> flags...", count=len(flag_tag_map))

        try:
            flags = list(flag_tag_map.keys())
            results = submit_flags(flags)
        except Exception as e:
            channel.basic_nack(delivery_tag=max(flag_tag_map.values()), multiple=True, requeue=True)
            logger.error(
                "Failed to submit <b>{count}</> flags. Exception: {exception}. Message: {exception_msg}",
                count=len(flags),
                exception=type(e).__name__,
                exception_msg=e,
            )

            for flag in flags:
                attempt = flag_attempt_map[flag]
                channel.basic_publish(
                    exchange="",
                    routing_key="flag.persistence",
                    body=FlagPersistMessage(
                        value=flag,
                        status="requeued" if attempt < config.submitter.retries else "failed",
                        attempts=attempt,
                    ).model_dump_json(),
                    properties=pika.BasicProperties(delivery_mode=2),
                )
        else:
            stats = Counter(status for status, _, _ in results)
            logger.info(
                "<b>{accepted}</> accepted, <b>{rejected}</> rejected, <b>{requeued}</> requeued.",
                accepted=stats.get("accepted", 0),
                rejected=stats.get("rejected", 0),
                requeued=stats.get("requeued", 0),
            )

            for status, response, flag in results:
                if status != "requeued":
                    channel.basic_ack(flag_tag_map[flag])
                else:
                    channel.basic_reject(flag_tag_map[flag], requeue=True)

                channel.basic_publish(
                    exchange="",
                    routing_key="flag.persistence",
                    body=FlagPersistMessage(
                        value=flag,
                        status=status,
                        response=response,
                        attempts=flag_attempt_map[flag],
                    ).model_dump_json(),
                    properties=pika.BasicProperties(delivery_mode=2),
                )


def start_stream_consumer(channel, submit_flag: StreamSubmitFunction) -> None:
    """
    Starts the stream consumer that listens to the 'flag.submission' queue and processes incoming flags
    one by one using the user-defined submit function.
    """

    def callback(ch, method, properties, body) -> None:
        flag: str = body.decode().strip()
        attempt: int = properties.headers.get("x-delivery-count", 0) if properties.headers else 0

        if attempt:
            logger.info(
                "<b>{flag}</> resubmitting ({retry}/{limit})...",
                flag=flag,
                retry=attempt,
                limit=config.submitter.retries,
            )

        status: Literal["accepted", "rejected", "requeued", "failed"]

        try:
            status, response, exception = *submit_flag(flag), None
        except Exception as e:
            status, response, exception = "requeued", None, e

        match status:
            case "accepted":
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.success("<b>{flag}</> accepted. Response: {response}", flag=flag, response=response)
            case "rejected":
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.warning("<b>{flag}</> rejected. Response: {response}", flag=flag, response=response)
            case "requeued":
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)

                if attempt >= config.submitter.retries:
                    log_msg = "<b>{flag}</> failed to submit, max retries reached."
                    status = "failed"
                else:
                    log_msg = "<b>{flag}</> requeued."

                if exception:
                    logger.error(
                        log_msg + " Exception: {exception}. Message: {exception_msg}",
                        flag=flag,
                        exception=type(exception).__name__,
                        exception_msg=exception,
                    )
                elif response:
                    logger.error(log_msg + " Response: {response}", flag=flag, response=response)
                else:
                    logger.error(log_msg, flag=flag)
            case _:
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                logger.error("<b>{flag}</> got unknown status '{status}'.", flag=flag, status=status)
                status = "failed"

        ch.basic_publish(
            exchange="",
            routing_key="flag.persistence",
            body=FlagPersistMessage(
                value=flag,
                status=status,
                response=response,
                attempts=attempt,
            ).model_dump_json(),
            properties=pika.BasicProperties(delivery_mode=2),
        )

    logger.info("Waiting for flags...")
    channel.basic_consume(queue="flag.submission", on_message_callback=callback)
    channel.start_consuming()


def start_batch_consumer(channel, submit_flags: BatchSubmitFunction) -> None:  # noqa: C901
    """
    Starts the batch consumer that listens to the 'flag.submission' queue and processes incoming flags
    in batches using the user-defined submit function.
    """
    flag_tag_map: dict[str, int] = {}
    flag_attempt_map: dict[str, int] = {}

    last_submission_time = time.time()

    def is_queue_idle():
        """
        Provides an alternative trigger for processing batches to prevent flags from staying in the queue for too long.
        """
        return time.time() - last_submission_time > config.submitter.batch_idle_timeout.total_seconds()

    def callback(ch, method, properties, body) -> None:
        tag: int = method.delivery_tag
        flag: str = body.decode().strip()
        attempt: int = properties.headers.get("x-delivery-count", 0) if properties.headers else 0

        flag_tag_map[flag] = tag
        flag_attempt_map[flag] = attempt

        logger.info(
            "<b>{flag}</> received. {count}/{max} flags in buffer.",
            flag=flag,
            count=len(flag_tag_map),
            max=config.submitter.batch_size,
        )

        if len(flag_tag_map) >= config.submitter.batch_size or is_queue_idle():  # type: ignore
            process_batch()

    def process_batch():
        nonlocal last_submission_time
        last_submission_time = time.time()

        logger.info("Submitting <b>{count}</> flags...", count=len(flag_tag_map))

        try:
            flags = list(flag_tag_map.keys())
            results = submit_flags(flags)
        except Exception as e:
            channel.basic_nack(delivery_tag=max(flag_tag_map.values()), multiple=True, requeue=True)
            logger.error(
                "Failed to submit <b>{count}</> flags. Exception: {exception}. Message: {exception_msg}",
                count=len(flags),
                exception=type(e).__name__,
                exception_msg=e,
            )

            for flag in flags:
                attempt = flag_attempt_map[flag]
                channel.basic_publish(
                    exchange="",
                    routing_key="flag.persistence",
                    body=FlagPersistMessage(
                        value=flag,
                        status="requeued" if attempt < config.submitter.retries else "failed",
                        attempts=attempt,
                    ).model_dump_json(),
                    properties=pika.BasicProperties(delivery_mode=2),
                )
        else:
            stats = Counter(status for status, _, _ in results)
            logger.info(
                "<b>{accepted}</> accepted, <b>{rejected}</> rejected, <b>{requeued}</> requeued.",
                accepted=stats.get("accepted", 0),
                rejected=stats.get("rejected", 0),
                requeued=stats.get("requeued", 0),
            )

            for status, response, flag in results:
                if status != "requeued":
                    channel.basic_ack(flag_tag_map[flag])
                else:
                    channel.basic_reject(flag_tag_map[flag], requeue=True)

                channel.basic_publish(
                    exchange="",
                    routing_key="flag.persistence",
                    body=FlagPersistMessage(
                        value=flag,
                        status=status,
                        response=response,
                        attempts=flag_attempt_map[flag],
                    ).model_dump_json(),
                    properties=pika.BasicProperties(delivery_mode=2),
                )

            flag_tag_map.clear()
            flag_attempt_map.clear()

    def trigger_batch_flushing():
        """
        Opens up a temporary connection to RabbitMQ and pushes a dummy message to the 'flag.submission' queue
        to trigger the consumer if it's idle for too long.
        """
        # TODO: Find a way to ignore dummy flags when submitting
        while True:
            if flag_tag_map and is_queue_idle():
                logger.info("Idle timeout reached with {count} flags in the queue.", count=len(flag_tag_map))
                connection, channel = connect_to_rabbitmq()
                channel.basic_publish(exchange="", routing_key="flag.submission", body="AVALA_PUSH")
                connection.close()
            time.sleep(1)

    logger.info("Waiting for flags...")
    threading.Thread(target=trigger_batch_flushing, daemon=True).start()
    channel.basic_consume(queue="flag.submission", on_message_callback=callback)
    channel.start_consuming()


def shutdown(*, connection, channel, teardown) -> None:
    """
    Shuts down the submitter by closing the connection, stopping the channel, and tearing down the context using
    the user-defined teardown function.
    """
    logger.info("Shutting down...")
    if teardown:
        logger.info("Tearing down context...")
        teardown()
        logger.info("Teardown complete.")
    if channel:
        channel.stop_consuming()
    if connection:
        connection.close()
    logger.info("Shutdown complete.")


def main() -> None:
    connection, channel = connect_to_rabbitmq()

    channel.queue_declare(
        queue="flag.submission",
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-delivery-limit": config.submitter.retries,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "flag.submission.dlq",
        },
    )
    channel.queue_declare(queue="flag.persistence")

    context = prepare_context()
    teardown_func = prepare_teardown_function(context)
    submit_func = prepare_submit_function(context)

    try:
        match determine_strategy():
            case "STREAM":
                start_stream_consumer(channel, submit_func)
            case "INTERVAL":
                start_interval_consumer(channel, submit_func)
            case "BATCH":
                start_batch_consumer(channel, submit_func)
    except (KeyboardInterrupt, SystemExit):
        shutdown(connection=connection, channel=channel, teardown=teardown_func)


if __name__ == "__main__":
    main()

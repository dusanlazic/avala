import asyncio
import inspect
import os
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timedelta
from importlib import import_module, reload
from typing import Any, Awaitable, Callable, Literal, TypeAlias, cast

import aio_pika
import pika
from avala.common.clock import game_has_started, get_tick_elapsed
from avala.common.config import config
from avala.common.logger import logger

StreamSubmitFunction: TypeAlias = Callable[
    [str],
    Awaitable[tuple[Literal["accepted", "rejected", "requeued"], str]],
]
BatchSubmitFunction: TypeAlias = Callable[
    [list[str]],
    Awaitable[list[tuple[Literal["accepted", "rejected", "requeued"], str, str]]],
]


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


def prepare_submit_function(submitter_context: Any) -> StreamSubmitFunction | BatchSubmitFunction:
    """
    Imports the user-defined submit function from the submitter module and fixes context argument
    if required by the function.
    """
    submit_func = import_user_function("submit")
    if not submit_func:
        logger.error("Submit function not found in user script.")
        exit(1)

    num_params = len(inspect.signature(submit_func).parameters)
    if num_params not in (1, 2):
        logger.error("Submit function should have exactly one or two arguments.")
        exit(1)

    async def wrapper(f: str | list[str]) -> Any:
        if inspect.iscoroutinefunction(submit_func):
            if num_params == 2:
                return await submit_func(f, submitter_context)
            else:
                return await submit_func(f)
        else:
            # TODO: Consider user-defined function thread safety carefully
            if num_params == 2:
                return await asyncio.to_thread(submit_func, f, submitter_context)
            else:
                return await asyncio.to_thread(submit_func, f)

    return wrapper


def prepare_teardown_function(submitter_context: Any) -> Callable[[], Awaitable[None]] | None:
    """
    Imports the user-defined teardown function from the submitter module if exists, and fixes context argument
    if required by the function.
    """
    teardown_func = import_user_function("teardown")
    if not teardown_func:
        return None

    num_params = len(inspect.signature(teardown_func).parameters)
    if num_params > 1:
        logger.error("Teardown function should not have more than one argument.")
        exit(1)

    async def wrapper():
        if inspect.iscoroutinefunction(teardown_func):
            if num_params == 1:
                await teardown_func(submitter_context)
            else:
                await teardown_func()
        else:
            if num_params == 1:
                teardown_func(submitter_context)
            else:
                teardown_func()

    return wrapper


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


async def connect_to_rabbitmq() -> tuple[
    aio_pika.abc.AbstractRobustConnection | None, aio_pika.abc.AbstractChannel | None
]:
    """
    Connects to RabbitMQ using the configuration settings and returns the connection and channel objects.
    """
    try:
        connection = await aio_pika.connect_robust(
            host=config.rabbitmq.host,
            port=config.rabbitmq.port,
            login=config.rabbitmq.user,
            password=config.rabbitmq.password,
        )
        channel = await connection.channel()
        logger.success("Connected to RabbitMQ.")
        return connection, channel
    except Exception as e:
        logger.error(
            "Failed to connect to RabbitMQ. <b>{error}</>: {error_msg}",
            error=type(e).__name__,
            error_msg=e,
        )

    return None, None


async def prepare_context() -> Any:
    """
    Imports and executes the user-definted setup function from the submitter module, if present.
    """
    setup_func = import_user_function("setup")
    if not setup_func:
        return None

    if inspect.iscoroutinefunction(setup_func):
        return await setup_func()
    else:
        return setup_func()


async def start_interval_consumer(queue: aio_pika.abc.AbstractQueue, submit_flags: BatchSubmitFunction) -> None:  # noqa: C901
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
            await asyncio.sleep(sleep_for)
            queue_cleared = False

        buffer: dict[str, aio_pika.abc.AbstractIncomingMessage] = {}

        for _ in range(config.submitter.batch_size):  # type: ignore
            try:
                message = await queue.get(fail=False)
            except Exception:
                message = None

            if message:
                flag: str = message.body.decode().strip()
                buffer[flag] = message
            else:
                queue_cleared = True
                break

        if not buffer:
            logger.info("No flags to submit.")
            continue

        logger.info("Submitting <b>{count}</> flags...", count=len(buffer))

        try:
            flags = list(buffer.keys())
            results = await submit_flags(flags)
        except Exception as e:
            for message in buffer.values():
                await message.reject(requeue=True)

            logger.error(
                "Failed to submit <b>{count}</> flags. Exception: {exception}. Message: {exception_msg}",
                count=len(flags),
                exception=type(e).__name__,
                exception_msg=e,
            )

            for flag in flags:
                message = buffer[flag]
                attempt = message.headers.get("x-delivery-count", 0) if message.headers else 0
                status = "requeued" if attempt < config.submitter.retries else "failed"
                # PERISTENCE HAPPENS HERE
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
                    await buffer[flag].ack()
                else:
                    await buffer[flag].reject(requeue=True)
                # PERISTENCE HAPPENS HERE


async def start_stream_consumer(queue: aio_pika.abc.AbstractQueue, submit_flag: StreamSubmitFunction) -> None:
    """
    Starts the stream consumer that listens to the 'flag.submission' queue and processes incoming flags
    one by one using the user-defined submit function.
    """

    async def process_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
        flag: str = message.body.decode().strip()
        attempt = message.headers.get("x-delivery-count", 0) if message.headers else 0

        if attempt:
            logger.info(
                "<b>{flag}</> resubmitting ({retry}/{limit})...",
                flag=flag,
                retry=attempt,
                limit=config.submitter.retries,
            )

        status: Literal["accepted", "rejected", "requeued", "failed"]

        try:
            status, response, exception = *(await submit_flag(flag)), None
        except Exception as e:
            status, response, exception = "requeued", None, e

        match status:
            case "accepted":
                await message.ack()
                logger.success("<b>{flag}</> accepted. Response: {response}", flag=flag, response=response)
            case "rejected":
                await message.ack()
                logger.warning("<b>{flag}</> rejected. Response: {response}", flag=flag, response=response)
            case "requeued":
                await message.reject(requeue=True)

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
                await message.reject(requeue=False)
                logger.error("<b>{flag}</> got unknown status '{status}'.", flag=flag, status=status)
                status = "failed"

        # PERISTENCE HAPPENS HERE

    logger.info("Waiting for flags...")
    await queue.consume(process_message)


async def start_batch_consumer(queue: aio_pika.abc.AbstractQueue, submit_flags: BatchSubmitFunction) -> None:  # noqa: C901
    """
    Starts the batch consumer that listens to the 'flag.submission' queue and processes incoming flags
    in batches using the user-defined submit function.

    TODO: Reimplement as async
    """
    raise NotImplementedError

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


async def shutdown(
    *,
    connection: aio_pika.abc.AbstractConnection,
    channel: aio_pika.abc.AbstractChannel,
    teardown: Callable | None,
) -> None:
    """
    Shuts down the submitter by closing the connection, stopping the channel, and tearing down the context using
    the user-defined teardown function.
    """
    logger.info("Shutting down...")

    if teardown:
        logger.info("Tearing down context...")
        await teardown()
        logger.info("Teardown complete.")

    if channel:
        await channel.close()

    if connection:
        await connection.close()

    logger.info("Shutdown complete.")


async def main() -> None:
    connection, channel = await connect_to_rabbitmq()
    if not connection or not channel:
        exit(1)

    queue = await channel.declare_queue(
        "flag.submission",
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-delivery-limit": config.submitter.retries,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "flag.submission.dlq",
        },
    )

    context = await prepare_context()
    teardown_func = prepare_teardown_function(context)
    submit_func = prepare_submit_function(context)

    try:
        match determine_strategy():
            case "STREAM":
                await start_stream_consumer(queue, cast(StreamSubmitFunction, submit_func))
            case "INTERVAL":
                await start_interval_consumer(queue, cast(BatchSubmitFunction, submit_func))
            case "BATCH":
                await start_batch_consumer(queue, cast(BatchSubmitFunction, submit_func))
    except (KeyboardInterrupt, SystemExit):
        await shutdown(connection=connection, channel=channel, teardown=teardown_func)


if __name__ == "__main__":
    asyncio.run(main())

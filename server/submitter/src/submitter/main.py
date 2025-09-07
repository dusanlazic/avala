import asyncio
import inspect
import sys
from collections import Counter
from datetime import datetime, timedelta
from importlib import reload
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType
from typing import Any, Awaitable, Callable, Literal, TypeAlias, cast

import aio_pika
from avala.common.clock import game_has_started, get_tick_elapsed
from avala.common.config import config
from avala.common.logger import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

StreamSubmitFunction: TypeAlias = Callable[
    [str],
    Awaitable[tuple[Literal["accepted", "rejected", "requeued"], str]],
]
BatchSubmitFunction: TypeAlias = Callable[
    [list[str]],
    Awaitable[list[tuple[Literal["accepted", "rejected", "requeued"], str, str]]],
]


def determine_strategy() -> Literal["INTERVAL", "STREAM"]:
    """
    Determines the submission strategy based on the fields present in the submitter configuration.
    """
    field_strategy_map = {
        frozenset(["interval", "batch_size"]): "INTERVAL",
        frozenset(["per_tick", "batch_size"]): "INTERVAL",
        frozenset(["stream"]): "STREAM",
    }
    allowed_fields = set().union(*field_strategy_map.keys())

    present_fields = frozenset(config.submitter.model_dump(exclude_none=True).keys() & allowed_fields)
    return field_strategy_map[present_fields]  # type: ignore


def import_submitter_module() -> ModuleType:
    """
    Dynamically imports the submitter module.
    """
    script_path = config.submitter.script_path
    module_name = "submitter_script"

    if module_name in sys.modules:
        return reload(sys.modules[module_name])

    spec = spec_from_file_location(module_name, script_path)
    if spec and spec.loader:
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[module_name] = module
        return module

    raise ImportError("Failed to import the submitter module.")


def prepare_submit_function(submitter_context: Any, module: ModuleType) -> StreamSubmitFunction | BatchSubmitFunction:
    """
    Imports the user-defined submit function from the submitter module and fixes context argument
    if required by the function.
    """
    submit_func = getattr(module, "submit", None)
    if not submit_func:
        logger.error("Submit function not found in user script.")
        exit(1)

    num_params = len(inspect.signature(submit_func).parameters)
    if num_params not in (1, 2):
        logger.error("Submit function should have exactly one or two arguments.")
        exit(1)

    async def wrapper(f: str | list[str]) -> Any:
        args = (f, submitter_context) if num_params == 2 else (f,)

        if inspect.iscoroutinefunction(submit_func):
            return await submit_func(*args)
        elif config.submitter.threading:
            return await asyncio.to_thread(submit_func, *args)
        else:
            return submit_func(*args)

    return wrapper


def prepare_teardown_function(submitter_context: Any, module: ModuleType) -> Callable[[], Awaitable[None]] | None:
    """
    Imports the user-defined teardown function from the submitter module if exists, and fixes context argument
    if required by the function.
    """
    teardown_func = getattr(module, "teardown", None)
    if not teardown_func:
        return None

    num_params = len(inspect.signature(teardown_func).parameters)
    if num_params > 1:
        logger.error("Teardown function should not have more than one argument.")
        exit(1)

    async def wrapper():
        args = (submitter_context,) if num_params == 1 else ()

        if inspect.iscoroutinefunction(teardown_func):
            await teardown_func(*args)
        else:
            teardown_func(*args)

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
    else:
        interval = config.game.tick_duration

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


async def connect_to_db() -> async_sessionmaker[AsyncSession]:
    """
    Connects to the database using the configuration settings and returns the AsyncSessionLocal factory.
    """
    try:
        async_engine = create_async_engine(
            "postgresql+asyncpg://%s:%s@%s:%d/%s"
            % (
                config.database.user,
                config.database.password,
                config.database.host,
                config.database.port,
                config.database.name,
            ),
            pool_size=80,
            max_overflow=10,
        )
        AsyncSessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=async_engine,
        )
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        logger.success("Connected to the database.")
        return AsyncSessionLocal
    except Exception as e:
        logger.error(
            "Failed to connect to the database. <b>{error}</>: {error_msg}",
            error=type(e).__name__,
            error_msg=e,
        )
        raise e


async def prepare_context(module: ModuleType) -> Any:
    """
    Imports and executes the user-definted setup function from the submitter module, if present.
    """
    setup_func = getattr(module, "setup", None)
    if not setup_func:
        return None

    if inspect.iscoroutinefunction(setup_func):
        return await setup_func()
    else:
        return setup_func()


async def persist_flag_status(
    db: async_sessionmaker[AsyncSession],
    flag: str,
    status: Literal["accepted", "rejected", "requeued", "failed"],
    response: str | None = None,
):
    async with db() as session:
        try:
            await session.execute(
                text("UPDATE flag SET status = :status, response = :response WHERE value = :flag;"),
                {"status": status.upper(), "response": response, "flag": flag},
            )
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(
                "Failed to update flag status in the database. <b>{error}</>: {error_msg}",
                error=type(e).__name__,
                error_msg=e,
            )


async def start_interval_consumer(  # noqa: C901
    queue: aio_pika.abc.AbstractQueue,
    db: async_sessionmaker[AsyncSession],
    submit_flags: BatchSubmitFunction,
):  # noqa: C901
    """
    Starts the stream consumer that listens to the 'flag.submission' queue and processes incoming flags
    one by one using the user-defined submit function.
    """

    async def process_messages(
        messages: dict[str, aio_pika.abc.AbstractIncomingMessage],
    ) -> None:
        try:
            flags = list(messages.keys())
            results = await submit_flags(flags)
        except Exception as e:
            for message in messages.values():
                await message.reject(requeue=True)

            logger.error(
                "Failed to submit <b>{count}</> flags. Exception: {exception}. Message: {exception_msg}",
                count=len(flags),
                exception=type(e).__name__,
                exception_msg=e,
            )

            for flag in flags:
                message = messages[flag]
                attempt = message.headers.get("x-delivery-count", 0) if message.headers else 0
                status = "requeued" if attempt < config.submitter.retries else "failed"
                await persist_flag_status(db=db, flag=flag, response=None, status=status)  # type: ignore[arg-type]
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
                    await messages[flag].ack()
                else:
                    await messages[flag].reject(requeue=True)

            for status, response, flag in results:
                if status != "requeued":
                    await persist_flag_status(db=db, flag=flag, response=response, status=status)

    while True:
        sleep_for = calculate_next_submit_time().total_seconds()
        logger.info(
            "Next submission scheduled at <b>"
            + (datetime.now() + timedelta(seconds=sleep_for)).strftime("%H:%M:%S")
            + "</>."
        )
        await asyncio.sleep(sleep_for)

        queue_cleared = False
        while not queue_cleared:
            messages: dict[str, aio_pika.abc.AbstractIncomingMessage] = {}

            for _ in range(config.submitter.batch_size):
                message = await queue.get(fail=False)
                if message:
                    flag: str = message.body.decode().strip()
                    messages[flag] = message
                else:
                    queue_cleared = True

            if messages:
                asyncio.create_task(process_messages(messages))
            else:
                logger.info("No more flags to submit.")


async def start_stream_consumer(  # noqa: C901
    queue: aio_pika.abc.AbstractQueue,
    db: async_sessionmaker[AsyncSession],
    submit_flag: StreamSubmitFunction,
) -> None:
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
                logger.success(
                    "<b>{flag}</> accepted. Response: {response}",
                    flag=flag,
                    response=response,
                )
            case "rejected":
                await message.ack()
                logger.warning(
                    "<b>{flag}</> rejected. Response: {response}",
                    flag=flag,
                    response=response,
                )
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
                logger.error(
                    "<b>{flag}</> got unknown status '{status}'.",
                    flag=flag,
                    status=status,
                )
                status = "failed"

        await persist_flag_status(db=db, flag=flag, status=status)

    logger.info("Waiting for flags...")
    await queue.consume(process_message)

    try:
        await asyncio.Future()  # Wait forever
    finally:
        logger.info("Consumer stopped.")


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


async def start() -> None:
    connection, channel = await connect_to_rabbitmq()
    db_session_factory = await connect_to_db()

    if not connection or not channel or not db_session_factory:
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

    submitter_module = import_submitter_module()

    context = await prepare_context(submitter_module)
    teardown_func = prepare_teardown_function(context, submitter_module)
    submit_func = prepare_submit_function(context, submitter_module)

    try:
        match determine_strategy():
            case "STREAM":
                await start_stream_consumer(queue, db_session_factory, cast(StreamSubmitFunction, submit_func))
            case "INTERVAL":
                await start_interval_consumer(queue, db_session_factory, cast(BatchSubmitFunction, submit_func))
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        await shutdown(connection=connection, channel=channel, teardown=teardown_func)


def main():
    asyncio.run(start())


if __name__ == "__main__":
    main()

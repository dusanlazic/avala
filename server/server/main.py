from contextlib import asynccontextmanager

from avala.common.logger import logger
from fastapi import FastAPI

from configure.routes import router as configure_router
from database import init_db
from flag_ids.routes import router as flag_ids_router
from flags.routes import router as flags_router
from messaging import connect_to_rabbitmq, declare_submission_queue
from workers.routes import router as workers_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Avala server...")

    # Initialize the database
    await init_db()

    # Connect to RabbitMQ
    connection, channel = await connect_to_rabbitmq()
    if not connection or not channel:
        logger.error("Failed to connect to RabbitMQ. Exiting...")
        raise SystemExit(1)

    await declare_submission_queue(channel)
    app.state.connection = connection
    app.state.channel = channel

    yield

    await channel.close()
    await connection.close()

    logger.info("Stopping Avala server...")


app = FastAPI(
    title="Avala Server",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok"}


for router in [
    workers_router,
    configure_router,
    flags_router,
    flag_ids_router,
]:
    app.include_router(router)

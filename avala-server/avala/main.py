import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from avala_shared.logs import config as log_config
from avala_shared.logs import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .broadcast import broadcast, emitter
from .config import DOT_DIR_PATH, config
from .database import create_tables
from .mq.monitoring import aggregate_flags
from .mq.rabbit_async import RabbitQueue, rabbit
from .routes.attack_data import router as attack_data_router
from .routes.connect import router as connect_router
from .routes.flags import router as flags_router
from .routes.statistics import router as statistics_router
from .scheduler import initialize_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_dot_dir()
    await create_tables()
    emitter.connect()
    await broadcast.connect()
    await rabbit.connect()

    submission_queue = await RabbitQueue(
        channel=rabbit.channel,
        routing_key="submission_queue",
        durable=True,
    ).declare()
    persisting_queue = await RabbitQueue(
        channel=rabbit.channel,
        routing_key="persisting_queue",
        durable=True,
    ).declare()

    rabbit.add_queue(submission_queue)
    rabbit.add_queue(persisting_queue)

    scheduler = initialize_scheduler()
    scheduler.start()

    asyncio.create_task(aggregate_flags())

    yield

    logger.info("Shutting down...")
    await rabbit.close()
    await broadcast.disconnect()
    emitter.disconnect()
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


def main():
    app.include_router(flags_router)
    app.include_router(connect_router)
    app.include_router(attack_data_router)
    app.include_router(statistics_router)

    configure_cors(app)
    configure_static(app)

    try:
        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
            log_config=configure_logging(),
        )
    except KeyboardInterrupt:
        logger.info("Thanks for using Avala!")


def configure_logging():
    """
    Configures the main logger and disables the default Uvicorn logger.
    """
    logger.configure(**log_config)

    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["loggers"]["uvicorn"]["handlers"] = []
    uvicorn_log_config["loggers"]["uvicorn.error"]["handlers"] = []
    uvicorn_log_config["loggers"]["uvicorn.access"]["handlers"] = []
    return uvicorn_log_config


def configure_cors(app: FastAPI):
    """
    Configures CORS middleware if the Avala backend and web UI are hosted on different domains.
    """
    if config.server.cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=(config.server.cors),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def configure_static(app: FastAPI):
    """
    Configures the static files serving if the web UI is served by the backend.
    """
    if not config.server.frontend:
        return

    source_code_dir = Path(__file__).resolve().parent
    static_folder_path = source_code_dir / "static" / "dist"
    app.mount("", StaticFiles(directory=static_folder_path, html=True), name="static")

    logger.info("Serving frontend.")


def create_dot_dir():
    """
    Creates the .avala directory if it doesn't exist for storing temporary files.
    """
    if not DOT_DIR_PATH.exists():
        DOT_DIR_PATH.mkdir()
        logger.info("Created .avala directory.")
    else:
        logger.info("Found .avala directory.")


if __name__ == "__main__":
    main()

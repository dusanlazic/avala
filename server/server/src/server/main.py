from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from avala.common.config import config
from avala.common.logger import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .configure.routes import router as configure_router
from .database import init_db
from .flag_ids.routes import router as flag_ids_router
from .flags.routes import router as flags_router
from .messaging import connect_to_rabbitmq, declare_submission_queue
from .scheduling import init_scheduler
from .stats.routes import router as stats_router
from .workers.routes import router as workers_router


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

    # Initialize the scheduler
    scheduler = init_scheduler()
    scheduler.start()

    logger.success("Avala server started.")
    yield

    await channel.close()
    await connection.close()

    scheduler.shutdown(wait=False)

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
    stats_router,
]:
    app.include_router(router)

# Enable CORS if configured
if config.server.cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.server.cors),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info("CORS enabled for origins: %s" % ", ".join(config.server.cors))

# Serve static files if configured
if config.server.dashboard:
    source_code_dir = Path(__file__).resolve().parent
    static_folder_path = source_code_dir / "static" / "dist"
    app.mount("", StaticFiles(directory=static_folder_path, html=True), name="static")

    logger.info("Serving dashboard at /")

# Disable the default Uvicorn logging handlers
uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
uvicorn_log_config["loggers"]["uvicorn"]["handlers"] = []
uvicorn_log_config["loggers"]["uvicorn.error"]["handlers"] = []
uvicorn_log_config["loggers"]["uvicorn.access"]["handlers"] = []

uvicorn.run(
    app,
    host=config.server.host,
    port=config.server.port,
    log_config=uvicorn_log_config,
)

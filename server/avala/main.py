import shutil
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .mq.rabbit_async import rabbit, RabbitQueue
from .shared.logs import logger
from .shared.logs import config as log_config
from .routes.flags import router as flags_router
from .routes.connect import router as connect_router
from .routes.attack_data import router as attack_data_router
from .routes.statistics import router as statistics_router
from .database import setup_db_conn, create_tables
from .config import get_config, Config, DOT_DIR_PATH
from .scheduler import initialize_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_dot_dir()
    setup_db_conn()
    create_tables()
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

    # await broadcast.connect()
    scheduler = initialize_scheduler()
    scheduler.start()

    yield

    logger.info("Shutting down...")
    await rabbit.close()
    # await broadcast.disconnect()
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


def main():
    config = get_config()

    app.include_router(flags_router)
    app.include_router(connect_router)
    app.include_router(attack_data_router)
    app.include_router(statistics_router)

    configure_cors(app, config)
    configure_static(app, config)

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


def configure_cors(app: FastAPI, config: Config):
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


def configure_static(app: FastAPI, config: Config):
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


def initialize_workspace():
    """
    Initializes the workspace in the current working directory by creating starter
    configuration files and scripts.
    """
    logger.info("Initializing workspace...")
    source_code_dir = Path(__file__).resolve().parent
    initialization_dir = source_code_dir / "initialization"
    workspace_dir = Path.cwd()

    for item in initialization_dir.iterdir():
        if item.name == "__pycache__":
            continue

        destination = workspace_dir / item.name
        if destination.exists():
            logger.info(
                "⏩ Skipping creating {item_name} as it already exists.",
                item_name=item.name,
            )
            continue
        shutil.copy2(item, destination)
        logger.info("✅ Created {item_name}.", item_name=item.name)

    logger.success(
        """🎉 Workspace initialized. Next steps:

 <b>1.</> 📝 <strike>Run <b>avl init</> to initialize your server workspace.</>
 <b>2.</> 🔧 Configure the server by editing <b>server.yaml</b>.
 <b>3.</> 🧩 Implement the flag submission logic in <b>submitter.py</b>.
 <b>4.</> 🧩 Implement the flag ID fetching logic in <b>flag_ids.py</b>.
 <b>5.</> 📝 Run <b>avl test</> to ensure everything is set up correctly.
 <b>6.</> 🐳 Edit <b>compose.yaml</> to fit your infrastructure.
 <b>7.</> 🚀 Run <b>docker compose up -d</> to run everything.
 <b>8.</> 🎉 Happy hacking!
        """
    )


if __name__ == "__main__":
    main()

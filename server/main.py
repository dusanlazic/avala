import os
import uvicorn
from shared.logs import logger
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from shared.logs import config as log_config
from .mq.rabbit_async import rabbit, RabbitQueue
from .database import connect_database, disconnect_database
from .routes.flags import router as flags_router
from .config import config, load_user_config, DOT_DIR_PATH
from .models import create_tables
from .scheduler import initialize_scheduler
from .websocket import sio, socketio


@asynccontextmanager
async def lifespan(app: FastAPI):
    show_banner()

    create_dot_dir()

    connect_database()
    create_tables()

    await rabbit.connect()
    await rabbit.create_queue("submission_queue", durable=True)

    scheduler = initialize_scheduler()
    scheduler.start()

    yield

    print()  # Add a newline after the ^C
    logger.info("Shutting down...")
    await rabbit.close()

    disconnect_database()


app = FastAPI(lifespan=lifespan)


def main():
    load_user_config()

    app.include_router(flags_router)
    configure_cors(app)
    configure_socketio(app)

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
    logger.configure(**log_config)

    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["loggers"]["uvicorn"]["handlers"] = []
    uvicorn_log_config["loggers"]["uvicorn.error"]["handlers"] = []
    uvicorn_log_config["loggers"]["uvicorn.access"]["handlers"] = []
    return uvicorn_log_config


def configure_cors(app: FastAPI):
    dev_origins = ["*"]
    prod_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=(
            dev_origins
            if os.environ.get("PYTHON_ENV") == "development"
            else prod_origins
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def configure_static(app: FastAPI):
    base_dir = Path(__file__).resolve().parent
    static_folder_path = base_dir / ".." / "frontend" / "dist"
    app.mount("", StaticFiles(directory=static_folder_path), name="static")


def configure_socketio(app: FastAPI):
    app.mount("/", socketio.ASGIApp(sio))


def create_dot_dir():
    if not DOT_DIR_PATH.exists():
        DOT_DIR_PATH.mkdir()
        logger.info("Created .fast directory.")
    else:
        logger.info("Found .fast directory.")


def show_banner():
    print(
        f"""
\033[32;1m     .___    ____\033[0m    ______         __ 
\033[32;1m    /   /\__/   /\033[0m   / ____/_  ____ / /_  
\033[32;1m   /   /   /  ❬` \033[0m  / /_/ __ `/ ___/ __/
\033[32;1m  /___/   /____\ \033[0m / __/ /_/ (__  ) /_  
\033[32;1m /    \___\/     \033[0m/_/  \__,_/____/\__/  
\033[32;1m/\033[0m                      \033[32mserver\033[0m \033[2mv%s\033[0m
"""
        % "2.0.0"
    )


if __name__ == "__main__":
    main()

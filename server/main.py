import os
import sys
import uvicorn
import socketio
from loguru import logger
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from playhouse.postgres_ext import PostgresqlExtDatabase
from shared.logs import TextStyler as st
from shared.logs import config as log_config
from .database import db
from .routes.flags import router as flags_router
from .config import config, load_user_config, DOT_DIR_PATH
from .models import Client, Exploit, Flag
from .scheduler import initialize_scheduler

app = FastAPI()
app.include_router(flags_router)

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")


def main():
    show_banner()

    configure_cors()
    configure_static()
    configure_socketio()
    uvicorn_logging = configure_logging()

    create_dot_dir()
    load_user_config()

    connect_database()
    setup_database()

    scheduler = initialize_scheduler()
    scheduler.start()

    uvicorn.run(
        app,
        host=config["server"]["host"],
        port=config["server"]["port"],
        log_config=uvicorn_logging,
    )


def show_banner():
    vers = "2.0.0"
    print(
        f"""
\033[32;1m     .___    ____\033[0m    ______         __ 
\033[32;1m    /   /\__/   /\033[0m   / ____/_  ____ / /_  
\033[32;1m   /   /   /  ❬` \033[0m  / /_/ __ `/ ___/ __/
\033[32;1m  /___/   /____\ \033[0m / __/ /_/ (__  ) /_  
\033[32;1m /    \___\/     \033[0m/_/  \__,_/____/\__/  
\033[32;1m/\033[0m                      \033[32mserver\033[0m \033[2mv{vers}\033[0m
"""
    )


def configure_logging():
    logger.configure(**log_config)

    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["loggers"]["uvicorn"]["handlers"] = []
    uvicorn_log_config["loggers"]["uvicorn.error"]["handlers"] = []
    uvicorn_log_config["loggers"]["uvicorn.access"]["handlers"] = []
    return uvicorn_log_config


def configure_cors():
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


def configure_static():
    base_dir = Path(__file__).resolve().parent
    static_folder_path = base_dir / "dist"
    app.mount("", StaticFiles(directory=static_folder_path), name="static")


def configure_socketio():
    app.mount("/", socketio.ASGIApp(sio))


def create_dot_dir():
    if not DOT_DIR_PATH.exists():
        DOT_DIR_PATH.mkdir()
        logger.info("Created .fast directory.")
    else:
        logger.info("Found .fast directory.")


def connect_database():
    postgres = PostgresqlExtDatabase(
        config["database"]["name"],
        user=config["database"]["user"],
        password=config["database"]["password"],
        host=config["database"]["host"],
        port=config["database"]["port"],
    )

    db.initialize(postgres)
    try:
        db.connect()
    except Exception as e:
        logger.error(
            f"An error occurred when connecting to the database:\n{st.color(e, 'red')}"
        )
        sys.exit(1)

    logger.info("Connected to the database.")


def setup_database():
    db.create_tables([Client, Exploit, Flag])
    Flag.add_index(Flag.value)

    logger.info("Created tables and indexes.")


# @sio.on("connect")
# async def connect(sid, env):
#     print("New Client Connected to This id :" + " " + str(sid)) @ sio.on("disconnect")


# async def disconnect(sid):
#     print("Client Disconnected: " + " " + str(sid))


@app.get("/")
def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    main()

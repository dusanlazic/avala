import os
import sys
import yaml
import uvicorn
import socketio
from loguru import logger
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from shared.util import deep_update
from shared.logs import TextStyler as st
from shared.logs import config as log_config
from shared.validation import validate_data
from .validation.custom import validate_delay, validate_interval
from .validation.schemas import server_yaml_schema

app = FastAPI()
sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")

config = {
    "game": {},
    "submitter": {"module": "submitter"},
    "server": {"host": "0.0.0.0", "port": 2023},
    "database": {
        "name": "fast",
        "user": "admin",
        "password": "admin",
        "host": "localhost",
        "port": 5432,
    },
}


def main():
    show_banner()

    configure_cors()
    configure_static()
    configure_socketio()
    uvicorn_logging = configure_logging()

    create_dot_dir()
    load_user_config()

    uvicorn.run(
        "server:app",
        host="localhost",
        port=2023,
        lifespan="on",
        reload=True,
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
    uvicorn_log_config["loggers"]["uvicorn"]["propagate"] = False
    uvicorn_log_config["loggers"]["uvicorn.error"]["propagate"] = False
    uvicorn_log_config["loggers"]["uvicorn.access"]["propagate"] = False
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
    dot_dir_path = ".fast"
    if not os.path.exists(dot_dir_path):
        os.makedirs(dot_dir_path)
        logger.success("Created .fast directory.")
    else:
        logger.success(".fast directory already exists.")


def load_user_config():
    # Remove datetime resolver
    # https://stackoverflow.com/a/52312810
    yaml.SafeLoader.yaml_implicit_resolvers = {
        k: [r for r in v if r[0] != "tag:yaml.org,2002:timestamp"]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    user_config = -1

    for ext in ["yml", "yaml"]:
        if os.path.isfile(f"server.{ext}"):
            with open(f"server.{ext}", "r") as file:
                user_config = yaml.safe_load(file)
                break

    if not user_config:
        logger.error("No configuration found in server.yaml. Exiting...")
        exit(1)

    if user_config == -1:
        logger.error(
            "server.yaml not found in the current working directory. Exiting..."
        )
        exit(1)

    if not validate_data(
        user_config, server_yaml_schema, custom=[validate_delay, validate_interval]
    ):
        logger.error("Fix errors in server.yaml and rerun.")
        exit(1)

    deep_update(config, user_config)

    # Wrap single team ip in a list
    if type(config["game"]["team_ip"]) != list:
        config["game"]["team_ip"] = [config["game"]["team_ip"]]


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

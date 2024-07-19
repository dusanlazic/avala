import os
import uvicorn
from shared.logs import logger
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from shared.logs import config as log_config
from .mq.rabbit_async import rabbit
from .routes.flags import router as flags_router
from .routes.connect import router as connect_router
from .routes.flag_ids import router as flag_ids_router
from .routes.statistics import router as statistics_router
from .database import create_tables
from .config import config, load_user_config, DOT_DIR_PATH
from .scheduler import initialize_scheduler
from .websocket import sio, socketio


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_dot_dir()
    create_tables()

    await rabbit.connect()
    await rabbit.create_queue("submission_queue", durable=True)

    scheduler = initialize_scheduler()
    scheduler.start()

    yield

    print()  # Add a newline after the ^C
    logger.info("Shutting down...")
    await rabbit.close()
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


def main():
    show_banner()
    load_user_config()

    app.include_router(flags_router)
    app.include_router(connect_router)
    app.include_router(flag_ids_router)
    app.include_router(statistics_router)

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
    dev_origins = ["http://localhost:5173"]
    prod_origins = ["http://localhost:5173"]

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
        logger.info("Created .avala directory.")
    else:
        logger.info("Found .avala directory.")


def show_banner():
    print(
        """\033[32;1m
      db 
     ;MM:
    ,V^MM. 7MM""Yq.  ,6"Yb.  `7M""MMF',6"Yb.  
   ,M  `MM `MM   j8 8)   MM    M  MM 8)   MM  
   AbmmmqMA MM""Yq.  ,pm9MM   ,P  MM  ,pm9MM  
  A'     VML`M   j8 8M   MM . d'  MM 8M   MM  
.AMA.   .AMMA.mmm9' `Moo9^Yo8M' .JMML`Moo9^Yo.
\033[0m"""
    )


if __name__ == "__main__":
    main()

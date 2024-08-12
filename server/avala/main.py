import shutil
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .mq.rabbit_async import rabbit
from .shared.logs import logger
from .shared.logs import config as log_config
from .routes.flags import router as flags_router
from .routes.connect import router as connect_router
from .routes.attack_data import router as attack_data_router
from .routes.statistics import router as statistics_router
from .database import setup_db_conn, create_tables
from .config import config, load_user_config, DOT_DIR_PATH
from .scheduler import initialize_scheduler
from .broadcast import broadcast


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_dot_dir()
    setup_db_conn()
    create_tables()
    await rabbit.connect()
    await rabbit.create_queue("submission_queue", durable=True)
    await rabbit.create_queue("persisting_queue", durable=True)
    await broadcast.connect()
    scheduler = initialize_scheduler()
    scheduler.start()

    yield

    print()  # Add a newline after the ^C
    logger.info("Shutting down...")
    await rabbit.close()
    await broadcast.disconnect()
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


def main():
    show_banner()
    load_user_config()

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
    logger.configure(**log_config)

    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["loggers"]["uvicorn"]["handlers"] = []
    uvicorn_log_config["loggers"]["uvicorn.error"]["handlers"] = []
    uvicorn_log_config["loggers"]["uvicorn.access"]["handlers"] = []
    return uvicorn_log_config


def configure_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=(config.server.cors),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def configure_static(app: FastAPI):
    if not config.server.frontend:
        return

    source_code_dir = Path(__file__).resolve().parent
    static_folder_path = source_code_dir / "static" / "dist"
    app.mount("", StaticFiles(directory=static_folder_path, html=True), name="static")

    logger.info("Serving frontend.")


def create_dot_dir():
    if not DOT_DIR_PATH.exists():
        DOT_DIR_PATH.mkdir()
        logger.info("Created .avala directory.")
    else:
        logger.info("Found .avala directory.")


def initialize_workspace():
    logger.info("Initializing workspace...")
    source_code_dir = Path(__file__).resolve().parent
    initialization_dir = source_code_dir / "initialization"
    workspace_dir = Path.cwd()

    for item in initialization_dir.iterdir():
        if item.name == "__pycache__":
            continue

        destination = workspace_dir / item.name
        if destination.exists():
            logger.info(f"Skipping {item.name} as it already exists.")
            continue
        shutil.copy2(item, destination)
        logger.info(f"Created {item.name}.")

    logger.success(
        """Workspace initialized. Next steps:

 <b>1.</> 🔧 Configure the server by editing <b>server.yaml</b>.
 <b>2.</> 🧩 Implement the flag submission logic in <b>submitter.py</b>.
 <b>3.</> 🧩 Implement the flag ID fetching logic in <b>flag_ids.py</b>.
 <b>4.</> 🐳 Edit <b>compose.yaml</> to fit your infrastructure.
 <b>5.</> 🚀 Run <b>docker compose up -d</> to run everything.
        """
    )


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

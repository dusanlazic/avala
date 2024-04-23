import sys
from loguru import logger
from peewee import DatabaseProxy
from playhouse.postgres_ext import PostgresqlExtDatabase
from shared.logs import TextStyler as st
from .config import config

db = DatabaseProxy()


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

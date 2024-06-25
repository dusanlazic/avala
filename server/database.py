import sys
from shared.logs import logger
from peewee import DatabaseProxy
from playhouse.postgres_ext import PostgresqlExtDatabase
from .config import config

db = DatabaseProxy()


def connect_database():
    postgres = PostgresqlExtDatabase(
        config.database.name,
        user=config.database.user,
        password=config.database.password,
        host=config.database.host,
        port=config.database.port,
    )

    db.initialize(postgres)
    try:
        db.connect()
    except Exception as e:
        logger.error(
            "An error occurred when connecting to the database:\n<red>%s</red>" % e
        )
        sys.exit(1)

    logger.info("Connected to the database.")

import sys
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import config
from .shared.logs import logger


engine = None
SessionLocal = None
Base = declarative_base()


def setup_db_conn():
    global engine, SessionLocal

    if engine is not None and SessionLocal is not None:
        return

    try:
        engine = create_engine(
            "postgresql://%s:%s@%s:%s/%s"
            % (
                config.database.user,
                config.database.password,
                config.database.host,
                config.database.port,
                config.database.name,
            )
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except Exception as e:
        logger.error(
            "An error occurred when connecting to the database:\n<red>{error}</red>",
            error=e,
        )
        sys.exit(1)


@contextmanager
def get_db_context():
    setup_db_conn()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    with get_db_context() as db:
        yield db


def create_tables():
    Base.metadata.create_all(bind=engine)


def test_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection established.")
    except Exception as e:
        logger.error(
            "An error occurred when connecting to the database:\n<red>{error}</red>",
            error=e,
        )
        sys.exit(1)

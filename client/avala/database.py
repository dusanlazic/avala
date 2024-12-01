from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .api_client.client import DOT_DIR_PATH
from .logging import logger

DOT_DIR_PATH.mkdir(exist_ok=True)

engine = create_engine(
    "sqlite:///%s" % (DOT_DIR_PATH / "database.db").resolve().as_posix()
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)


def test_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("SQLite database connection established.")
    except Exception as e:
        logger.error(
            "An error occurred when connecting to the database:\n<red>{error}</red>",
            error=e,
        )
        raise

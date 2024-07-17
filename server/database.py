import sys
from shared.logs import logger
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import config

SQLALCHEMY_DATABASE_URL = f"postgresql://{config.database.user}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.name}"

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error(
        "An error occurred when connecting to the database:\n<red>%s</red>" % e
    )
    sys.exit(1)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection established.")
    except Exception as e:
        logger.error(
            "An error occurred when connecting to the database:\n<red>%s</red>" % e
        )
        sys.exit(1)

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from .config import config

Base = declarative_base()


sync_engine = create_engine(config.database.dsn(driver="psycopg2"))
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


async_engine = create_async_engine(config.database.dsn(driver="asyncpg"))
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
)


@contextmanager
def get_sync_db_session() -> Iterator[Session]:
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


def get_sync_db():
    with get_sync_db_session() as db:
        yield db


@asynccontextmanager
async def get_async_db_session() -> AsyncIterator[AsyncSession]:
    db = AsyncSessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db():
    async with get_async_db_session() as db:
        yield db


async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

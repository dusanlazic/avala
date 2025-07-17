import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, AsyncIterator

from avala.common.config import config
from broadcaster import Broadcast
from fastapi import Depends
from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

POSTGRESQL_URL = "postgresql+asyncpg://%s:%s@%s:%d/%s" % (
    config.database.user,
    config.database.password,
    config.database.host,
    config.database.port,
    config.database.name,
)

broadcast = Broadcast(POSTGRESQL_URL.replace("postgresql+asyncpg", "postgresql"))


class Base(DeclarativeBase):
    pass


async_engine = create_async_engine(POSTGRESQL_URL, pool_size=80, max_overflow=10)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
)


@asynccontextmanager
async def get_async_db_session() -> AsyncIterator[AsyncSession]:
    """Dependency that provides a database session."""
    db = AsyncSessionLocal()
    try:
        yield db
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


async def get_async_db():
    async with get_async_db_session() as db:
        yield db


Database = Annotated[AsyncSession, Depends(get_async_db)]


async def init_db() -> None:
    """Initialize the database."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def to_snake_case(name: str) -> str:
    """Convert a camel case string to snake case."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


class BaseModel(Base):
    __abstract__ = True

    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:
        return to_snake_case(cls.__name__)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=None,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Variable(Base):
    __tablename__ = "variables"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=True)


class StateManager:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get(self, name: str) -> str | None:
        result = await self._db.execute(select(Variable).where(Variable.name == name))
        var = result.scalar_one_or_none()
        return var.value if var else None

    async def set(self, name: str, value: str) -> None:
        result = await self._db.execute(select(Variable).where(Variable.name == name))
        var = result.scalar_one_or_none()
        if var:
            var.value = value
        else:
            self._db.add(Variable(name=name, value=value))
        await self._db.commit()

    async def delete(self, name: str) -> None:
        result = await self._db.execute(select(Variable).where(Variable.name == name))
        var = result.scalar_one_or_none()
        if var:
            await self._db.delete(var)
            await self._db.commit()

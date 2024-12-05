from sqlalchemy import Boolean, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class FlagIdsHash(Base):
    """
    SQLAlchemy model representing a hash generated from the exploit alias, target, and the flag ID value for a specific
    tick.
    """

    __tablename__ = "hashes"

    value: Mapped[str] = mapped_column(String, primary_key=True)


class StoredObject(Base):
    """
    SQLAlchemy model representing a stored blob in the database.
    """

    __tablename__ = "objects"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[bytes] = mapped_column(LargeBinary)


class PendingFlag(Base):
    """
    SQLAlchemy model representing a pending flag in the database.
    """

    __tablename__ = "pending_flags"

    value: Mapped[str] = mapped_column(String, primary_key=True)
    target: Mapped[str] = mapped_column(String)
    alias: Mapped[str] = mapped_column(String)
    submitted: Mapped[bool] = mapped_column(Boolean, default=False)

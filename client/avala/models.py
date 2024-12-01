from sqlalchemy import Boolean, Column, LargeBinary, String

from .database import Base


class FlagIdsHash(Base):
    """
    SQLAlchemy model representing a hash generated from the exploit alias, target, and the flag ID value for a specific tick.
    """

    __tablename__ = "hashes"

    value = Column(String, primary_key=True)


class StoredObject(Base):
    """
    SQLAlchemy model representing a stored blob in the database.
    """

    __tablename__ = "objects"

    key = Column(String, primary_key=True)
    value = Column(LargeBinary)


class PendingFlag(Base):
    """
    SQLAlchemy model representing a pending flag in the database.
    """

    __tablename__ = "pending_flags"

    value = Column(String, primary_key=True)
    target = Column(String)
    alias = Column(String)
    submitted = Column(Boolean, default=False)

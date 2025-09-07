import enum

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from server.database import BaseModel


class SubmissionOutcome(enum.StrEnum):
    QUEUED = "queued"
    REQUEUED = "requeued"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class Flag(BaseModel):
    value: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    host: Mapped[str] = mapped_column(String)
    tick: Mapped[int] = mapped_column(Integer)
    service: Mapped[str] = mapped_column(String, nullable=True)
    worker: Mapped[str] = mapped_column(String)
    exploit: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[SubmissionOutcome] = mapped_column(Enum(SubmissionOutcome), default=SubmissionOutcome.QUEUED)
    response: Mapped[str] = mapped_column(String, nullable=True)

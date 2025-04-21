from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from server.database import BaseModel


class Worker(BaseModel):
    alias: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    dev_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    ip: Mapped[str] = mapped_column(String, nullable=False)
    registered_exploits: Mapped[str] = mapped_column(String, nullable=False)

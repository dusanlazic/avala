from typing import Literal

from pydantic import BaseModel, Field


class FlagPersistMessage(BaseModel):
    value: str
    status: Literal["accepted", "rejected", "requeued", "failed"]
    response: str | None = None
    attempts: int = Field(default=0)

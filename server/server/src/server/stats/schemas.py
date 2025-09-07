from typing import Literal

from pydantic import BaseModel


class TotalNumbersResponse(BaseModel):
    queued: int
    accepted: int
    rejected: int
    accepted_previous_tick: int
    rejected_previous_tick: int


class CurrentTickResponse(BaseModel):
    queued: int
    accepted: int
    rejected: int
    accepted_delta: int
    rejected_delta: int


class FlagUpdateMessage(BaseModel):
    host: str
    service: str
    exploit: str
    status: Literal["queued", "accepted", "rejected", "discarded"]
    delta: int

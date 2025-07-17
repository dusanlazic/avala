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

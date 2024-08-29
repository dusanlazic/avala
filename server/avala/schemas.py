from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class FlagSubmissionResponse(BaseModel):
    value: str
    status: str
    response: str

    @field_validator("status")
    @classmethod
    def status_must_be_one_of(cls, v: str) -> str:
        if v not in ["accepted", "rejected", "requeued"]:
            raise ValueError(
                "Status must be one of 'accepted', 'rejected' or 'requeued'."
            )
        return v


class FlagEnqueueRequest(BaseModel):
    values: list[str]
    exploit: str
    target: str


class FlagEnqueueResponse(BaseModel):
    enqueued: int
    discarded: int


class SearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tick: int
    timestamp: datetime
    player: str
    exploit: str
    target: str
    status: str
    value: str
    response: str | None


class SearchPagingMetadata(BaseModel):
    current: int
    last: int
    has_next: bool = Field(serialization_alias="hasNext")
    has_prev: bool = Field(serialization_alias="hasPrev")


class SearchStatsMetadata(BaseModel):
    total: int
    fetched: int
    execution_time: float = Field(serialization_alias="executionTime")


class SearchMetadata(BaseModel):
    results: SearchStatsMetadata
    paging: SearchPagingMetadata


class SearchResults(BaseModel):
    results: list[SearchResult]
    metadata: SearchMetadata


class DatabaseViewStats(BaseModel):
    current_tick: int
    last_tick: int
    manual: int
    total: int


class TickStats(BaseModel):
    tick: int
    accepted: int


class ExploitAcceptedFlagsForTick(BaseModel):
    tick: int
    accepted: int


class ExploitAcceptedFlagsHistory(BaseModel):
    name: str
    history: list[ExploitAcceptedFlagsForTick]

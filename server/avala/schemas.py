from typing import Any
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


class SearchQueryParams(BaseModel):
    query: str | None = None
    page: int = Field(1, ge=1)
    show: int = Field(25, le=100)
    sort: list[str] | None = None


class SearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tick: int
    timestamp: str
    player: str
    exploit: str
    target: str
    status: str
    value: str
    response: str


class SearchPagingMetadata(BaseModel):
    current: int
    last: int
    has_next: bool = Field(alias="hasNext")
    has_prev: bool = Field(alias="hasPrev")


class SearchStatsMetadata(BaseModel):
    total: int
    fetched: int
    execution_time: float = Field(alias="executionTime")


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

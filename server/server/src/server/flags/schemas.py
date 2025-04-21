from pydantic import BaseModel


class FlagEnqueueBody(BaseModel):
    values: set[str]
    host: str
    worker: str
    service: str | None = None
    exploit: str | None = None


class FlagEnqueueResponse(BaseModel):
    enqueued: int
    discarded: int

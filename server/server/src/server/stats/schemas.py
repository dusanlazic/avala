from pydantic import BaseModel


class TotalNumbersResponse(BaseModel):
    queued: int
    accepted: int
    rejected: int

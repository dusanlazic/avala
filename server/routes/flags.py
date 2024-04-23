from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from server.auth import basic_auth
from server.models import Flag
from server.database import db
from server.scheduler import get_tick_number

router = APIRouter(prefix="/flags", tags=["Flags"])


class EnqueueBody(BaseModel):
    values: list[str]
    exploit: str
    player: str
    target: str


@router.post("/queue")
def enqueue(flags: EnqueueBody, _: Annotated[str, Depends(basic_auth)]):
    with db.connection_context():
        duplicate_flags = Flag.select(Flag.value).where(Flag.value.in_(flags.values))
        duplicate_flag_values = [flag.value for flag in duplicate_flags]

        new_flags = [
            {
                "value": value,
                "exploit": flags.exploit,
                "target": flags.target,
                "tick": get_tick_number(),
                "player": flags.player,
                "status": "queued",
            }
            for value in flags.values
            if value not in duplicate_flag_values
        ]

    Flag.insert_many(new_flags).on_conflict_ignore().execute()

    return {
        "discarded": duplicate_flag_values,
        "enqueued": [flag.value for flag in new_flags],
    }

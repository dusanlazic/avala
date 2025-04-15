from fastapi import APIRouter

from database import Database
from messaging import Channel

from . import service
from .schemas import FlagEnqueueBody, FlagEnqueueResponse

router = APIRouter(prefix="/flags", tags=["flags"])


@router.post("/", response_model=FlagEnqueueResponse)
async def enqueue_flag(flags: FlagEnqueueBody, db: Database, ch: Channel):
    """
    Enqueue a flag for processing.
    """
    enqueued, discarded = await service.enqueue_flags(
        flags.values,
        flags.host,
        flags.service,
        flags.worker,
        flags.exploit,
        db,
        ch,
    )

    return FlagEnqueueResponse(enqueued=enqueued, discarded=discarded)

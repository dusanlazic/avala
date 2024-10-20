from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..broadcast import broadcast
from ..config import config
from ..database import get_sync_db
from ..models import Flag
from ..scheduler import get_tick_number
from ..schemas import (
    DashboardViewStats,
    DatabaseViewStats,
    ExploitAcceptedFlagsForTick,
    ExploitAcceptedFlagsHistory,
    TickStats,
)

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/dashboard", response_model=DashboardViewStats)
def dashboard_view_stats(
    db: Annotated[Session, Depends(get_sync_db)],
    username: CurrentUser,
) -> DashboardViewStats:
    expiration_time = datetime.now() - timedelta(seconds=config.game.flag_ttl)

    accepted = db.query(Flag).filter(Flag.status == "accepted").count()
    rejected = db.query(Flag).filter(Flag.status == "rejected").count()

    queued = (
        db.query(Flag)
        .filter(Flag.status == "queued", Flag.timestamp >= expiration_time)
        .count()
    )
    return DashboardViewStats(accepted=accepted, rejected=rejected, queued=queued)


@router.get("/database", response_model=DatabaseViewStats)
def database_view_stats(
    db: Annotated[Session, Depends(get_sync_db)],
    username: CurrentUser,
) -> DatabaseViewStats:
    current_tick = get_tick_number()

    current_tick_flags = db.query(Flag).filter(Flag.tick == current_tick).count()
    last_tick_flags = db.query(Flag).filter(Flag.tick == current_tick - 1).count()
    manually_submitted = (
        db.query(Flag)
        .filter(Flag.target == "unknown", Flag.exploit == "manual")
        .count()
    )
    total_flags = db.query(Flag).count()

    return DatabaseViewStats(
        current_tick=current_tick_flags,
        last_tick=last_tick_flags,
        manual=manually_submitted,
        total=total_flags,
    )


@router.get("/timeline", response_model=list[TickStats])
def timeline_view_stats(
    db: Annotated[Session, Depends(get_sync_db)],
    username: CurrentUser,
) -> list[TickStats]:
    current_tick = get_tick_number()

    tick_stats = dict(
        db.query(Flag.tick, func.count(Flag.id).label("count"))
        .filter(Flag.status == "accepted")
        .group_by(Flag.tick)
        .order_by(Flag.tick)
        .all()
    )

    return [
        TickStats(tick=tick, accepted=tick_stats.get(tick, 0))
        for tick in range(1, current_tick + 1)
    ]


@router.get("/exploits")
def exploits(
    db: Annotated[Session, Depends(get_sync_db)],
    username: CurrentUser,
):
    last_tick = get_tick_number() - 1
    ten_ticks_ago = last_tick - 9

    results = (
        db.query(Flag.exploit, Flag.tick, func.count(Flag.id).label("accepted_count"))
        .filter(Flag.status == "accepted", Flag.tick >= ten_ticks_ago)
        .group_by(Flag.exploit, Flag.tick)
        .order_by(Flag.exploit, Flag.tick)
        .all()
    )

    all_ticks = list(range(ten_ticks_ago, last_tick + 1))

    exploits_history: dict[str, ExploitAcceptedFlagsHistory] = {}
    for result in results:
        if result.exploit not in exploits_history:
            exploits_history[result.exploit] = ExploitAcceptedFlagsHistory(
                name=result.exploit,
                history=[
                    ExploitAcceptedFlagsForTick(tick=tick, accepted=0)
                    for tick in all_ticks
                ],
            )

        for item in exploits_history[result.exploit].history:
            if item.tick == result.tick:
                item.accepted = result.accepted_count

    return [history.dict() for history in exploits_history.values()]


@router.get("/stream/flags")
async def stream_flags(username: CurrentUser):
    return StreamingResponse(
        flags_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


async def flags_event_stream():
    async with broadcast.subscribe(channel="flags") as subscriber:
        async for event in subscriber:
            yield "data: %s\n\n" % event.message


@router.get("/stream/rabbit")
async def stream_rabbit(username: CurrentUser):
    return StreamingResponse(
        rabbit_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


async def rabbit_event_stream():
    try:
        async with broadcast.subscribe(channel="rabbit") as subscriber:
            async for event in subscriber:
                yield "data: %s\n\n" % event.message
    except:
        return

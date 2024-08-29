import json
import time
import requests
from typing import Annotated
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime
from requests.auth import HTTPBasicAuth
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from ..auth import CurrentUser
from ..config import AvalaConfig
from ..database import get_db
from ..models import Flag
from ..schemas import (
    DatabaseViewStats,
    TickStats,
    ExploitAcceptedFlagsForTick,
    ExploitAcceptedFlagsHistory,
)
from ..scheduler import get_tick_number

router = APIRouter(prefix="/stats", tags=["Statistics"])


def collect_stats(db: Session, config: AvalaConfig):
    while True:
        response = requests.get(
            f"http://{config.rabbitmq.host}:{config.rabbitmq.management_port}/api/queues/%2F/submission_queue",
            auth=HTTPBasicAuth(config.rabbitmq.user, config.rabbitmq.password),
            params={
                "lengths_age": 90,
                "lengths_incr": 1,
                "msg_rates_age": 90,
                "msg_rates_incr": 1,
                "data_rates_age": 90,
                "data_rates_incr": 1,
            },
        )
        data = response.json()

        try:
            submission_rate = int(data["message_stats"]["ack_details"]["rate"])
            submission_history = transform_rabbitmq_stats(
                data["message_stats"]["ack_details"]["samples"][::-1]
            )
        except KeyError:
            submission_rate = 0
            submission_history = []

        try:
            retrieval_rate = int(data["message_stats"]["publish_details"]["rate"])
            retrieval_history = transform_rabbitmq_stats(
                data["message_stats"]["publish_details"]["samples"][::-1]
            )
        except KeyError:
            retrieval_rate = 0
            retrieval_history = []

        queued_count = data["messages"]

        accepted_count = (
            db.query(func.count(Flag.id)).filter(Flag.status == "accepted").scalar()
        )
        rejected_count = (
            db.query(func.count(Flag.id)).filter(Flag.status == "rejected").scalar()
        )

        yield json.dumps(
            {
                "queued": queued_count,
                "accepted": accepted_count,
                "rejected": rejected_count,
                "submission": {"rate": submission_rate, "history": submission_history},
                "retrieval": {"rate": retrieval_rate, "history": retrieval_history},
            }
        ) + "\n"
        time.sleep(1)


transform_rabbitmq_stats = lambda items: list(
    map(
        lambda x, y: {
            "sample": x["sample"] - y["sample"],
            "timestamp": datetime.fromtimestamp(x["timestamp"] / 1000).strftime(
                "%H:%M:%S"
            ),
        },
        items[1:],
        items[:-1],
    )
)


@router.get("/database", response_model=DatabaseViewStats)
def database_view_stats(
    db: Annotated[Session, Depends(get_db)],
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
    db: Annotated[Session, Depends(get_db)],
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
    db: Annotated[Session, Depends(get_db)],
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

    return exploits_history.values()


@router.get("/subscribe")
def stats(
    db: Annotated[Session, Depends(get_db)],
    username: CurrentUser,
):
    return StreamingResponse(collect_stats(db), media_type="application/x-ndjson")


# async def broadcast_incoming_flags():
#     async with broadcast.subscribe(channel="incoming_flags") as subscription:
#         async for event in subscription:
#             yield json.dumps(event.message) + "\n"


# @router.get("/flags/subscribe")
# async def incoming_flags():
#     return StreamingResponse(
#         broadcast_incoming_flags(), media_type="application/x-ndjson"
#     )

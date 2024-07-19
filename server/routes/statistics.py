import json
import asyncio
import requests
from typing import Annotated
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime
from requests.auth import HTTPBasicAuth
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from server.config import config
from server.database import get_db
from server.models import Flag
from server.scheduler import get_tick_number
from server.broadcast import broadcast

router = APIRouter(prefix="/stats", tags=["Statistics"])


async def collect_stats(db: Session):
    params = {
        "lengths_age": 90,
        "lengths_incr": 1,
        "msg_rates_age": 90,
        "msg_rates_incr": 1,
        "data_rates_age": 90,
        "data_rates_incr": 1,
    }

    while True:
        response = requests.get(
            f"http://{config.rabbitmq.host}:15672/api/queues/%2F/submission_queue",
            auth=HTTPBasicAuth(config.rabbitmq.user, config.rabbitmq.password),
            params=params,
        )
        data = response.json()

        submission_rate = int(data["message_stats"]["ack_details"]["rate"])
        retrieval_rate = int(data["message_stats"]["publish_details"]["rate"])

        submission_history = transform_rabbitmq_stats(
            data["message_stats"]["ack_details"]["samples"][::-1]
        )
        retrieval_history = transform_rabbitmq_stats(
            data["message_stats"]["publish_details"]["samples"][::-1]
        )

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
        await asyncio.sleep(1)


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


@router.get("/subscribe")
async def stats(db: Annotated[Session, Depends(get_db)]):
    return StreamingResponse(collect_stats(db), media_type="application/x-ndjson")


@router.get("/exploits")
async def exploits(db: Annotated[Session, Depends(get_db)]):
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

    exploits_history = {}
    for result in results:
        if result.exploit not in exploits_history:
            exploits_history[result.exploit] = {
                "name": result.exploit,
                "history": [{"tick": tick, "accepted": 0} for tick in all_ticks],
            }
        # Update counts for ticks where flags were accepted
        for item in exploits_history[result.exploit]["history"]:
            if item["tick"] == result.tick:
                item["accepted"] = result.accepted_count

    response = [data for data in exploits_history.values()]
    return response


async def arriving_flags():
    async with broadcast.subscribe(channel="flag_reports") as subscriber:
        async for event in subscriber:
            yield json.dumps(event.message) + "\n"


@router.get("/exploits/subscribe")
async def live_exploits():
    return StreamingResponse(arriving_flags(), media_type="application/x-ndjson")

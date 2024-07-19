import json
import asyncio
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from server.config import config
from addict import Dict

router = APIRouter(prefix="/stats", tags=["Statistics"])


async def collect_queue_stats():
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

        queued_flags_count = data["messages"]

        yield json.dumps(
            {
                "queued": queued_flags_count,
                "submission": {"rate": submission_rate, "history": submission_history},
                "retrieval": {"rate": retrieval_rate, "history": retrieval_history},
            }
        ) + "\n"
        await asyncio.sleep(1)


@router.get("/queues")
async def queues():
    return StreamingResponse(collect_queue_stats(), media_type="application/x-ndjson")


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

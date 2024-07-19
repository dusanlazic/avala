import requests
from requests.auth import HTTPBasicAuth
from fastapi import APIRouter, Depends
from server.config import config
from addict import Dict

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/queues")
async def queues():
    vhost = "%2F"
    queue_name = "submission_queue"

    params = {
        "lengths_age": 90,
        "lengths_incr": 1,
        "msg_rates_age": 90,
        "msg_rates_incr": 1,
        "data_rates_age": 90,
        "data_rates_incr": 1,
    }

    response = requests.get(
        f"http://{config.rabbitmq.host}:15672/api/queues/{vhost}/{queue_name}",
        auth=HTTPBasicAuth(
            config.rabbitmq.user,
            config.rabbitmq.password,
        ),
        params=params,
    )
    data = Dict(response.json())

    submission_rate = int(data.message_stats.ack_details.rate)
    retrieval_rate = int(data.message_stats.publish_details.rate)

    submission_history = calculate_differences(
        [sample.sample for sample in data.message_stats.ack_details.samples][::-1]
    )
    retrieval_history = calculate_differences(
        [sample.sample for sample in data.message_stats.publish_details.samples][::-1]
    )

    queued_flags_count = data.messages

    return {
        "queued": queued_flags_count,
        "submission": {"rate": submission_rate, "history": submission_history},
        "retrieval": {"rate": retrieval_rate, "history": retrieval_history},
    }


calculate_differences = lambda numbers: list(
    map(lambda x, y: x - y, numbers[1:], numbers[:-1])
)

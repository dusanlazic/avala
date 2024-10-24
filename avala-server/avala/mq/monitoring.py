import json
from datetime import datetime
from queue import Queue

from ..broadcast import broadcast, emitter
from ..schemas import FlagCounterDelta

deltas_queue: Queue = Queue()


async def aggregate_flags():
    async with broadcast.subscribe(channel="flags") as subscriber:
        async for event in subscriber:
            deltas = FlagCounterDelta(**json.loads(event.message))
            deltas_queue.put(deltas)


def fetch_and_broadcast_rates():
    retrieved_count = 0
    submitted_count = 0

    while not deltas_queue.empty():
        delta = deltas_queue.get_nowait()
        if delta.queued > 0:
            retrieved_count += delta.queued
        elif delta.queued < 0:
            submitted_count += abs(delta.queued)

    timestamp = datetime.now().strftime("%H:%M:%S")

    emitter.emit(
        "rabbit",
        json.dumps(
            {
                "retrieved_per_second": retrieved_count,
                "submitted_per_second": submitted_count,
                "timestamp": timestamp,
            }
        ),
    )

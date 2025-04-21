from apscheduler.schedulers.asyncio import AsyncIOScheduler
from avala.common.clock import get_next_tick_start
from avala.common.config import config

from flag_ids import service as flag_ids_service


def init_scheduler():
    """
    Initializes the scheduler instance and schedules required jobs.
    """
    scheduler: AsyncIOScheduler = AsyncIOScheduler()

    scheduler.add_job(
        func=flag_ids_service.reload_flag_ids,
        trigger="interval",
        seconds=config.game.tick_duration.total_seconds(),
        next_run_time=get_next_tick_start(),
    )

    return scheduler

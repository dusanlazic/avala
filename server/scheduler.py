from loguru import logger
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from shared.logs import TextStyler as st
from .config import config


def initialize_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=tick_announcer,
        trigger="interval",
        seconds=get_tick_duration().seconds,
        id="tick_announcer",
        next_run_time=get_next_tick_start(),
    )
    return scheduler


def get_tick_duration():
    return timedelta(seconds=config["game"]["tick_duration"])


def get_first_tick_start():
    start_time_str = config["game"]["start_time"]
    return datetime.strptime(
        start_time_str,
        "%Y-%m-%d %H:%M:%S" if len(start_time_str) == 19 else "%Y-%m-%d %H:%M",
    )


def get_tick_elapsed(now=None):
    now = now or datetime.now()
    return (now - get_first_tick_start()) % get_tick_duration()


def get_tick_number(now=None):
    now = now or datetime.now()
    if now < get_first_tick_start():
        return -1

    return (now - get_first_tick_start()) // get_tick_duration()


def get_next_tick_start(now=None):
    now = now or datetime.now()
    if now < get_first_tick_start():
        return get_first_tick_start()

    return now + get_tick_duration() - get_tick_elapsed(now)


def tick_announcer():
    logger.info(
        f"Started tick {st.bold(get_tick_number())}. Next tick scheduled for {st.bold(get_next_tick_start().strftime('%H:%M:%S'))}. ⏱️"
    )

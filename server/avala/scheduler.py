from .shared.logs import logger
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from .attack_data import reload_attack_data
from .config import config


def initialize_scheduler():
    scheduler: BackgroundScheduler = BackgroundScheduler()

    now = datetime.now()
    scheduler.add_job(
        func=tick_announcer,
        trigger="interval",
        seconds=get_tick_duration().seconds,
        id="tick_announcer",
        next_run_time=get_next_tick_start(),
    )

    scheduler.add_job(
        func=reload_attack_data,
        trigger="interval",
        seconds=get_tick_duration().seconds,
        id="teams_json_reloader",
        next_run_time=get_next_tick_start(),
    )

    print_current_tick(now)
    return scheduler


def get_tick_duration() -> timedelta:
    return timedelta(seconds=config.game.tick_duration)


def get_first_tick_start() -> datetime:
    start_time_str = config.game.game_starts_at
    return datetime.strptime(
        start_time_str,
        "%Y-%m-%d %H:%M:%S" if len(start_time_str) == 19 else "%Y-%m-%d %H:%M",
    )


def get_networks_open_after() -> timedelta:
    return timedelta(
        hours=config.game.networks_open_after.hours or 0,
        minutes=config.game.networks_open_after.minutes or 0,
        seconds=config.game.networks_open_after.seconds or 0,
    )


def get_game_ends_after() -> timedelta:
    return timedelta(
        hours=config.game.game_ends_after.hours or 0,
        minutes=config.game.game_ends_after.minutes or 0,
        seconds=config.game.game_ends_after.seconds or 0,
    )


def get_networks_open_at() -> datetime:
    return get_first_tick_start() + get_networks_open_after()


def get_game_ends_at() -> datetime:
    return get_first_tick_start() + get_game_ends_after()


def get_network_open_at_tick() -> int:
    return (get_networks_open_at() - get_first_tick_start()) // get_tick_duration()


def get_game_ends_at_tick() -> int:
    return (get_game_ends_at() - get_first_tick_start()) // get_tick_duration()


def get_tick_elapsed(now=None) -> timedelta:
    now = now or datetime.now()
    if not game_has_started():
        return 0

    return (now - get_first_tick_start()) % get_tick_duration()


def get_tick_number(now=None) -> int:
    now = now or datetime.now()
    if not game_has_started():
        return 0

    return (now - get_first_tick_start()) // get_tick_duration() + 1


def get_next_tick_start(now=None) -> datetime:
    now = now or datetime.now()
    if not game_has_started():
        return get_first_tick_start()

    return now + get_tick_duration() - get_tick_elapsed(now)


def game_has_started(now=None) -> bool:
    now = now or datetime.now()
    return now >= get_first_tick_start()


def tick_announcer():
    logger.info(
        "Started tick <b>%d</>. Next tick scheduled for <b>%s</>."
        % (get_tick_number(), get_next_tick_start().strftime("%H:%M:%S"))
    )


def print_current_tick(now=None):
    if not game_has_started(now):
        logger.info(
            "Game has not started yet. First tick scheduled for <b>%s</>."
            % get_first_tick_start().strftime("%H:%M:%S")
        )
    else:
        logger.info(
            "Current tick is <b>%d</>. Next tick scheduled for <b>%s</>."
            % (get_tick_number(), get_next_tick_start().strftime("%H:%M:%S"))
        )

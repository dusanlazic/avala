from .shared.logs import logger
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from .attack_data import reload_attack_data
from .config import get_config
from .mq.monitoring import fetch_and_broadcast_rates

config = get_config()


def initialize_scheduler() -> BackgroundScheduler:
    """
    Initializes the APScheduler instance and schedules the tick announcer and attack data reloader.
    """
    scheduler: BackgroundScheduler = BackgroundScheduler()

    now = datetime.now()
    scheduler.add_job(
        func=tick_announcer,
        trigger="interval",
        seconds=config.game.tick_duration.seconds,
        id="tick_announcer",
        next_run_time=get_next_tick_start(),
    )

    scheduler.add_job(
        func=reload_attack_data,
        trigger="interval",
        seconds=config.game.tick_duration.seconds,
        id="attack_data_reloader",
        next_run_time=get_next_tick_start(),
    )

    scheduler.add_job(
        func=fetch_and_broadcast_rates,
        trigger="interval",
        seconds=1,
        id="rabbitmq_rates_emitter",
        next_run_time=(datetime.now() + timedelta(seconds=1)).replace(microsecond=0),
    )

    print_current_tick(now)
    return scheduler


def get_networks_open_at() -> datetime:
    return config.game.game_starts_at + config.game.networks_open_after


def get_game_ends_at() -> datetime:
    return config.game.game_starts_at + config.game.game_ends_after


def get_network_open_at_tick() -> int:
    return (
        get_networks_open_at() - config.game.game_starts_at
    ) // config.game.tick_duration


def get_game_ends_at_tick() -> int:
    return (
        get_game_ends_at() - config.game.game_starts_at
    ) // config.game.tick_duration


def get_tick_elapsed(now=None) -> timedelta:
    now = now or datetime.now()
    if not game_has_started():
        return 0

    return (now - config.game.game_starts_at) % config.game.tick_duration


def get_tick_number(now=None) -> int:
    now = now or datetime.now()
    if not game_has_started():
        return 0

    return (now - config.game.game_starts_at) // config.game.tick_duration + 1


def get_next_tick_start(now=None) -> datetime:
    now = now or datetime.now()
    if not game_has_started():
        return config.game.game_starts_at

    return now + config.game.tick_duration - get_tick_elapsed(now)


def game_has_started(now=None) -> bool:
    now = now or datetime.now()
    return now >= config.game.game_starts_at


def tick_announcer():
    """
    Logs the current tick number and the next tick's scheduled start time at the beginning of each tick.
    """
    logger.info(
        "Started tick <b>{tick_number}</>. Next tick scheduled for <b>{next_tick}</>.",
        tick_number=get_tick_number(),
        next_tick=get_next_tick_start().strftime("%H:%M:%S"),
    )


def print_current_tick(now=None):
    """
    Logs the current tick number and the next tick's scheduled start time. If the game has not started yet,
    it logs the first tick's scheduled start time.
    """
    if not game_has_started(now):
        logger.info(
            "Game has not started yet. First tick scheduled for <b>{first_tick}</>.",
            first_tick=config.game.game_starts_at.strftime("%H:%M:%S"),
        )
    else:
        logger.info(
            "Current tick is <b>{tick_number}</>. Next tick scheduled for <b>{next_tick}</>.",
            tick_number=get_tick_number(),
            next_tick=get_next_tick_start().strftime("%H:%M:%S"),
        )

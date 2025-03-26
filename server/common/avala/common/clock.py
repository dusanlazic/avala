from datetime import datetime, timedelta

from avala.common.config import config


def get_networks_open_at() -> datetime:
    return config.game.game_starts_at + config.game.networks_open_after


def get_game_ends_at() -> datetime:
    return config.game.game_starts_at + config.game.game_ends_after


def get_network_open_at_tick() -> int:
    return (get_networks_open_at() - config.game.game_starts_at) // config.game.tick_duration


def get_game_ends_at_tick() -> int:
    return (get_game_ends_at() - config.game.game_starts_at) // config.game.tick_duration


def get_tick_elapsed(now: datetime | None = None) -> timedelta:
    now = now or datetime.now()
    if not game_has_started():
        return timedelta(0)

    return (now - config.game.game_starts_at) % config.game.tick_duration


def get_tick_number(now: datetime | None = None) -> int:
    now = now or datetime.now()
    if not game_has_started():
        return 0

    return (now - config.game.game_starts_at) // config.game.tick_duration + 1


def get_next_tick_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    if not game_has_started():
        return config.game.game_starts_at

    return now + config.game.tick_duration - get_tick_elapsed(now)


def game_has_started(now: datetime | None = None) -> bool:
    now = now or datetime.now()
    return now >= config.game.game_starts_at

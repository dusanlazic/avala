import difflib
import hashlib
from datetime import datetime, timedelta

import pytz
import tzlocal


def convert_to_local_tz(dt_iso_str: str, tz: str) -> datetime:
    source_tz = pytz.timezone(tz)
    target_tz = tzlocal.get_localzone()

    dt = datetime.fromisoformat(dt_iso_str)
    dt_with_tz = source_tz.localize(dt)

    return dt_with_tz.astimezone(target_tz)


def get_next_tick_start(
    first_tick_start: datetime, tick_duration: timedelta
) -> datetime:
    now = datetime.now(tzlocal.get_localzone())
    if now < first_tick_start:
        return first_tick_start

    return now + tick_duration - ((now - first_tick_start) % tick_duration)


def did_you_mean(s: str, candidates: list[str]) -> str:
    match = difflib.get_close_matches(
        s,
        candidates,
    )
    if match:
        return "Did you mean <b>%s</>?" % match[0]
    return ""


colors = [
    # Red shades
    (255, 160, 122),
    (250, 128, 114),
    (240, 128, 128),
    (205, 92, 92),
    # Orange shades
    (255, 160, 122),
    (255, 127, 80),
    (255, 99, 71),
    (255, 69, 0),
    (255, 140, 0),
    (255, 165, 0),
    # Yellow shades
    (189, 183, 107),
    (240, 230, 140),
    (255, 218, 185),
    (250, 250, 210),
    (255, 215, 0),
    # Green shades
    (0, 128, 0),
    (46, 139, 87),
    (144, 238, 144),
    (50, 205, 50),
    (0, 255, 0),
    (173, 255, 47),
    # Blue shades
    (30, 144, 255),
    (135, 206, 235),
    (176, 224, 230),
    (70, 130, 180),
    (0, 206, 209),
    # Purple shades
    (219, 112, 147),
    (199, 21, 133),
    (255, 20, 147),
    (255, 105, 180),
    (255, 192, 203),
    # Pink shades
    (219, 112, 147),
    (199, 21, 133),
    (255, 20, 147),
    (255, 105, 180),
    (255, 192, 203),
    # Brown shades
    (210, 105, 30),
    (205, 133, 63),
    (188, 143, 143),
    (222, 184, 135),
    (255, 228, 196),
]


def hash_to_color(s):
    hash_hex = hashlib.md5(s.encode()).hexdigest()
    hash_dec = int(hash_hex, 16)
    return colors[hash_dec % len(colors)]


def colorize(s):
    r, g, b = hash_to_color(s)
    colored_string = f"\033[38;2;{r};{g};{b}m{s}\033[0m"
    return colored_string

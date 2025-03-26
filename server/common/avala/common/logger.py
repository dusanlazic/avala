import difflib
import hashlib
import sys
from typing import Iterable

from loguru import logger

LOGGER_CONFIG = {
    "handlers": [
        {
            "sink": sys.stdout,
            "format": "<d>[{time:HH:mm:ss}]</d> <level>{level: <8}</level> {message}",
        },
    ],
}

COLORS = [
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

logger = logger.opt(colors=True)
logger.configure(**LOGGER_CONFIG)  # type: ignore

_loguru_error = logger.error


def _custom_error(msg: str, *args, **kwargs) -> None:
    """
    Wraps error message with <red> tags turning the message red.

    :param msg: Message to be logged
    :type msg: str
    """
    _loguru_error(f"<red>{msg}</>", *args, **kwargs)


logger.error = _custom_error  # type: ignore


def _hash_to_color(s: str) -> tuple[int, int, int]:
    """
    Returns a color tuple based on the hash of the input string.

    :param s: Input string
    :type s: str
    :return: Tuple of RGB values
    :rtype: tuple[int, int, int]
    """
    hash_hex = hashlib.md5(s.encode()).hexdigest()
    hash_dec = int(hash_hex, 16)
    return COLORS[hash_dec % len(COLORS)]


def colorize(text: str, reset: str = "white") -> str:
    """
    Colorizes a string deterministically based on its hash. The same string will always
    have the same color.

    :param text: Input text to colorize
    :type text: str
    :param reset: Name or sequence to reset text color, defaults to `white`. Use `red` for error messages and ANSI
    escape codes for custom colors.
    :type reset: str, optional
    :return: Colored text
    :rtype: str
    """
    r, g, b = _hash_to_color(text)

    reset_color_map = {
        "white": "\033[0m",
        "red": "\033[0;31m",
        "dim": "\033[0;2m",
    }

    colored_string = f"\033[38;2;{r};{g};{b}m{text}{reset_color_map.get(reset, reset)}"
    return colored_string


def suggest_closest_match(input_string: str, candidates: Iterable[str]) -> str:
    """
    Suggests the most similar string from an iterable of possible strings.

    :param input_string: Input string to find the closest match for.
    :type input_string: str
    :param candidates: Iterable of possible strings.
    :type candidates: Iterable[str]
    :return: Suggested string.
    :rtype: str
    """
    matches = difflib.get_close_matches(input_string, candidates, n=1)
    if matches:
        return matches[0]
    return ""


def truncate(input_string: str, length: int = 50) -> str:
    """
    Truncates a string to a specified length and appends an ellipsis if the string is longer.

    :param input_string: Input string to truncate.
    :type input_string: str
    :param length: Maximum length of the string.
    :type length: int
    :return: Truncated string.
    :rtype: str
    """
    return (input_string[:length] + "...") if len(input_string) > length else input_string

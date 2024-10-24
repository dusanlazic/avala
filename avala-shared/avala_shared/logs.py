import sys

from loguru import logger

config = {
    "handlers": [
        {
            "sink": sys.stdout,
            "format": "<d>[{time:HH:mm:ss}]</d> <level>{level: <8}</level> {message}",
        },
    ],
}

logger = logger.opt(colors=True)
logger.configure(**config)

_error = logger.error


def error(msg: str, *args, **kwargs):
    _error(f"<red>{msg}</>", *args, **kwargs)


logger.error = error

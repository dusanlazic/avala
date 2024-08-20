from loguru import logger
import sys

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
    _error("<red>{msg}</>", msg=msg, *args, **kwargs)


logger.error = error

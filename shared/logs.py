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

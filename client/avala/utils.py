from .shared.util import colorize
from .shared.logs import logger


def debug(message, alias=None, target=None):
    if not alias or not target:
        logger.debug(message)
    else:
        logger.debug(
            "🔎 <bold>%s</>-><bold>%s</>: %s"
            % (colorize(alias), colorize(target), message)
        )

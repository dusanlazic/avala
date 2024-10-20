from avala_shared.logs import logger
from avala_shared.util import colorize


def debug(message: str, alias: str = None, target: str = None):
    """
    Prints a debug message to the console.

    :param message: Message to print
    :type message: str
    :param alias: Alias of the exploit for better log message visibility, defaults to None
    :type alias: str, optional
    :param target: Target for better log message visibility, defaults to None
    :type target: str, optional
    """
    if not alias or not target:
        logger.debug("{message}", message=message)
    else:
        logger.debug(
            "🔎 <b>{alias}</>-><b>{target}</>: {message}",
            alias=colorize(alias),
            target=colorize(target),
            message=message,
        )

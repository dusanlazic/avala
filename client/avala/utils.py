import inspect
from .shared.util import colorize
from .shared.logs import logger


def debug(message):
    try:
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        caller_func_name = caller_frame.f_code.co_name
        caller_globals = caller_frame.f_globals
        caller_func = caller_globals[caller_func_name]

        if hasattr(caller_func, "draft_exploit_config"):
            exploit_config = caller_func.draft_exploit_config
        elif hasattr(caller_func, "exploit_config"):
            exploit_config = caller_func.exploit_config

        target = next(iter(caller_frame.f_locals.values()), None)

        logger.debug(
            "🔎 <bold>%s</>-><bold>%s</>: %s"
            % (colorize(exploit_config.alias), colorize(target), message)
        )
    except Exception:
        logger.debug(message)

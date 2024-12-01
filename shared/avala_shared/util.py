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

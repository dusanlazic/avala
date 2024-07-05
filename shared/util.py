import pytz
import tzlocal
from datetime import datetime


def deep_update(left, right):
    """
    Update a dictionary recursively in-place.
    """
    for key, value in right.items():
        if isinstance(value, dict) and value:
            returned = deep_update(left.get(key, {}), value)
            left[key] = returned
        else:
            left[key] = right[key]
    return left


def convert_to_local_tz(dt_iso_str: str, tz: str):
    source_tz = pytz.timezone(tz)
    target_tz = tzlocal.get_localzone()

    dt = datetime.fromisoformat(dt_iso_str)
    dt_with_tz = source_tz.localize(dt)

    return dt_with_tz.astimezone(target_tz)

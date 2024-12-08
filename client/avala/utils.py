import difflib
from typing import Iterable


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

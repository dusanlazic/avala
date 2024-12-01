import difflib


def suggest_closest_match(input_string: str, candidates: list[str]) -> str:
    """
    Suggest the closest matching string from a list of candidates.

    :param input_string: The input string to find a match for.
    :type input_string: str
    :param candidates: A list of candidate strings to compare against.
    :type candidates: List[str]
    :return: A suggestion message with the closest match, or an empty string if no match is found.
    :rtype: str
    """
    matches = difflib.get_close_matches(input_string, candidates)
    if matches:
        return f"Did you mean <b>{matches[0]}</>?"
    return ""

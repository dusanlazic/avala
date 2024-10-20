from typing import Any

import requests


def fetch_json() -> dict | list:
    """
    Fetches raw flag IDs from the game server and returns them as a dictionary.
    Exceptions and retries are handled internally by Avala. It's advisable to
    set a timeout for requests to prevent the server from hanging indefinitely.

    :return: Raw flag IDs fetched from the game server.
    :rtype: dict | list
    """
    response = requests.get("https://ad.fbi.com/teams.json", timeout=5)
    return response.json()


def process_json(raw: dict) -> dict[str, dict[str, list[Any]]]:
    """
    Processes the raw flag IDs into a standardized, structured format.
    Flag IDs must be organized by service name and team IP address, and be stored
    in a list where each item corresponds to the flag IDs of a single tick.

    Example of the returned dictionary:
    {
        "SomeService": {
            "10.10.24.5": [
                "foo",   # Flag IDs of the most recent tick
                "bar",   # Flag IDs of the previous tick
                (...)
            ],
            (...)
        },
        (...)
    }

    Use type hints as a guide for the expected data structure.

    :param raw: Raw flag IDs as fetched from the game server.
    :type raw: dict
    :return: Processed flag IDs in a standardized structure.
    :rtype: dict[str, dict[str, list[Any]]]
    """
    processed: dict[str, dict[str, list[Any]]] = {}

    return processed

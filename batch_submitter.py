from queue import Queue
import requests


def submit(flags: list[str]) -> list[tuple[str, str, str]]:
    flag_responses = requests.post("http://example.ctf/flags", json=flags).json()

    ret = []
    for fr in flag_responses:
        value = fr["flag"]
        response = fr["response"]
        status = "accepted" if response.endswith("OK") else "rejected"
        ret.append((value, status, response))

    return ret

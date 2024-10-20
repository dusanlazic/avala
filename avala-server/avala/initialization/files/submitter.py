import requests
from pwn import *


def prepare():
    """
    This function is called before the server starts accepting flags.
    Use it to establish TCP connection to the server, etc. This function is
    optional, you can remove it completely if you don't need it.

    If the submit() function throws an exception, this function will be called
    again before retrying submission.
    """

    # The actual submitter from the "Compete With Team Czechia 2024" event.
    # Replace this code with your own.

    global r
    r = remote("172.19.1.5", 31337)
    r.recvuntil(b"\n\n")


def submit(flag: str) -> tuple[str, str, str]:
    """
    Submits a single flag to the flag checking service, classifies the response
    and returns the full response message. This function is used when flags are
    submitted one by one (e.g. over TCP).

    This function sends a single flag to the flag checking service, receives
    the response and returns a tuple containing the flag, status (should be
    "accepted", "rejected" or "requeued") and the full response message.

    :param flag: A flag to submit.
    :type flag: str
    :return: A tuple containing the flag, status ("accepted", "rejected", "requeued") and
    the full response message
    :rtype: tuple[str, str, str]
    """

    # The actual submitter from the "Compete With Team Czechia 2024" event.
    # Replace this code with your own.

    r.sendline(flag.encode())

    response = r.recvline().decode().strip()
    response_flag = response.split(" ")[0]

    if response.endswith("OK"):
        return response_flag, "accepted"
    if response.endswith("ERR"):
        return response_flag, "requeued"
    else:
        return response_flag, "rejected"


def submit(flags: list[str]) -> list[tuple[str, str, str]]:
    """
    Submits multiple flags to the flag checking service, classifies responses
    and returns full response messages. This function is used for submitting
    multiple flags at once (e.g. over HTTP).

    :param flags: Flags to submit.
    :type flags: list[str]
    :return: A list of tuples containing the flag, status ("accepted", "rejected"
    or "requeued") and the full response message.
    :rtype: list[tuple[str, str, str]]
    """

    # The actual submitter from the 2nd ECSC 2024 AD Demo event.
    # Replace this code with your own.

    responses = requests.put(
        "http://10.10.0.1:8080/flags",
        json=flags,
        headers={"X-Team-Token": "518d033ab65f175965de0850b6005628"},
    ).json()

    statuses = {
        "ACCEPTED": "accepted",
        "DENIED": "rejected",
        "RESUBMIT": "requeued",
        "ERROR": "requeued",
    }

    return [
        (
            response["flag"],
            statuses[response["status"]],
            response["msg"],
        )
        for response in responses
    ]


def cleanup():
    """
    This function is called when the server stops accepting flags. Use it to
    close TCP connection to the server, etc. This function is optional, you can
    remove it completely if you don't need it.

    If the submit() function throws an exception, this function will be called
    first, before calling prepare() and retrying submission.
    """
    r.close()

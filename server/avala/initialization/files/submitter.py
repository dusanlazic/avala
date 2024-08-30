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

    # Example code for establishing a TCP connection to the flag checking service.
    # Replace this code with your own.

    global r
    r = remote("fbi.com", 31337)
    r.recvuntil(b"\n\n")


def submit(flag: str) -> tuple[str, str, str]:
    """
    Submits a single flag to the flag checking service, classifies the response
    and returns the full response message. This function is used for submitting
    flags in a stream (e.g. over TCP).

    This function sends a single flag to the flag checking service, receives
    the response and returns a tuple containing the flag, status (should be
    "accepted", "rejected" or "requeued") and the full response message.

    :param flag: A flag to submit.
    :type flag: str
    :return: A tuple containing the flag, status ("accepted", "rejected", "requeued") and
    the full response message
    :rtype: tuple[str, str, str]
    """

    # Example code for submitting a flag over TCP.
    # Replace this code with your own.

    r.sendline(flag.encode())

    response = r.recvline().decode().strip()
    response_flag = response.split(" ")[0]

    if response.endswith("OK"):
        return response_flag, "accepted", response
    else:
        return response_flag, "rejected", response


def submit(flags: list[str]) -> list[tuple[str, str, str]]:
    """
    Submits multiple flags to the flag checking service, classifies responses
    and returns full response messages. This function is used for submitting
    multiple flags at once (e.g. over HTTP).

    :param flags: Flags to submit.
    :type flags: list[str]
    :return: A list of tuples containing the flag, status ("accepted" or "rejected)
    and the full response message.
    :rtype: list[tuple[str, str, str]]
    """

    # Example code for submitting flags over HTTP and classifying responses.
    # Replace this code with your own.

    flag_responses = requests.put(
        "http://fbi.com/flags",
        json=flags,
        headers={"X-Team-Token": "your-team-token"},
    ).json()

    return [
        (
            response["flag"],
            "accepted" if response["status"] == "ACCEPTED" else "rejected",
            response["msg"],
        )
        for response in flag_responses
        if "RESUBMIT" not in response["msg"]
    ]

    # Some AD game protocols return "RESUBMIT" responses indicating that
    # the flag should be resubmitted. In that case, just ommit the flag when
    # returning responses and Avala will consider it not submitted and retry
    # submission sometime.


def cleanup():
    """
    This function is called when the server stops accepting flags. Use it to
    close TCP connection to the server, etc. This function is optional, you can
    remove it completely if you don't need it.

    If the submit() function throws an exception, this function will be called
    first, before calling prepare() and retrying submission.
    """
    r.close()

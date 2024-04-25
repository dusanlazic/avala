# from pwn import *
from queue import Queue


def submit(queued: Queue[str], processed: Queue[tuple[str, str, str]]):
    # r = remote("flags.example.ctf", 1337)

    while True:
        flag = queued.get()
        response = "blahblah OK"
        status = "accepted" if response.endswith("OK") else "rejected"
        processed.put((flag, status, response))

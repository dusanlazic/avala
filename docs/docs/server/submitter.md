# Writing submitter script

To ensure compatibility with virtually any AD competition, Avala lets you write your own submitter script tailored to the competition’s requirements. This script, written by you, is responsible for the actual flag submission, while Avala ensures it executes smoothly and reliably.

Your submitter script must adhere to one of the templates specified below. If you like to learn by examples, you'll find them at the [bottom of the page](#examples).

As a first step, create a file named `submitter.py` in your directory.

---

## Script structure

You can submit flags in **batches** that are sent in fixed intervals, or in a single or multiple continuous **streams** submitting flags one by one. Both approaches will require you to write a function named `submit`, with optional `setup` and `teardown` functions described below.

### Batch submission

**Batch submission** is recommended for competitions that accept submitting multiple flags at once, typically via **HTTP**. Avala handles the submission by sending batches of flags at regular intervals and, if needed, will split large batches into smaller ones for safety. 

The `submit` function must accept a `list` of flags and is expected to return a `list` of `tuples`, where each tuple consists of a submission status (`"accepted"`, `"rejected"`, or `"requeued"`), a message from the service (`str`), and the original flag (`str`).

```py
from typing import Literal

def submit(flags: list[str]) -> list[tuple[Literal["accepted", "rejected", "requeued"], str, str]]:
    """
    Submits a list of flags and returns their status based on the flag checking 
    service's response. Returns a list of tuples, where each tuple contains the
    flag's status (accepted, rejected, or requeued), the response message, and 
    the original flag.

    Use this when the flag checking service allows submitting multiple flags
    at once (e.g. over HTTP).
    """

    return [
        ("accepted", "FLAG_3B37DF144CE4A83566BB OK", "FLAG_3B37DF144CE4A83566BB"),
        ("rejected", "FLAG_FEECD28345E360BA3775 OLD", "FLAG_FEECD28345E360BA3775")
    ]
```

### Stream submission

**Stream submission** should be used for competitions that accept flags one at the time, typically via **raw TCP**. Avala handles the submission by sending each flag immediatelly upon capture.

The `submit` function must accept a single flag (`str`) and is expected to return a `tuple` consisting of the submission status (`"accepted"`, `"rejected"`, or `"requeued"`) and the message from the service (`str`).

```py
from typing import Literal

def submit(flag: str) -> tuple[Literal["accepted", "rejected", "requeued"], str]:
    """
    Submits a single flag to the flag checking service. Returns a tuple
    containing the flag's status (accepted, rejected, or requeued)
    and the response message from the service.

    Use this when the flag checking service allows submitting only one flag
    at the time (e.g. over TCP).
    """

    return "accepted", "FLAG_3B37DF144CE4A83566BB OK"
```

!!! tip "Important"

    When submitting flags over TCP, it's much more efficient to reuse a single connection for submitting all the flags, which can be achieved with [persistent context](#persistent-context).

### Persistent context

If your submission process requires a persistent connection (e.g. `remote` from `pwn`), a session token (e.g. `Session` from `requests`), or any other shared state, you can manage the submission context using the `setup` and `teardown` functions.

- The `setup` function runs once at the beginning and returns an object that is passed to every `submit` call as the second argument.
- The `teardown` function runs during the shutdown process to clean up any resources, such as closing the connection.

All three functions, `submit`, `setup`, and `teardown`, can also be **coroutines** if you want to use `asyncio` and asynchronous libraries.


=== "Batch with context"

    ```py
    from typing import Any, Literal

    def setup() -> Any:
        """
        Gets called before the Avala server starts accepting flags. Use it to 
        establish a TCP connection to the flag submitting service, initiate a
        session, etc.
        
        Object returned from this function will be passed as the second argument
        to the submit function.
        """
        return {}

    def submit(flags: list[str], context: Any) -> list[tuple[Literal["accepted", "rejected", "requeued"], str, str]]:
        """
        Submits a list of flags and returns their status based on the flag checking 
        service's response. Returns a list of tuples, where each tuple contains the
        flag's status (accepted, rejected, or requeued), the response message, and 
        the original flag.

        Use this when the flag checking service allows submitting multiple flags
        at once (e.g. over HTTP).
        """

        return [
            ("accepted", "FLAG_3B37DF144CE4A83566BB OK", "FLAG_3B37DF144CE4A83566BB"),
            ("rejected", "FLAG_FEECD28345E360BA3775 OLD", "FLAG_FEECD28345E360BA3775")
        ]

    def teardown(context: Any):
        """
        Gets called during the shutdown process to clean up any resources,
        such as closing the connection and similar.
        """
        pass
    ```

=== "Stream with context"

    ```py
    from typing import Any, Literal

    def setup() -> Any:
        """
        Gets called before the Avala server starts accepting flags. Use it to 
        establish a TCP connection to the flag submitting service, initiate a
        session, etc.
        
        Object returned from this function will be passed as the second argument
        to the submit function.
        """
        return {}

    def submit(flag: str, context: Any) -> tuple[Literal["accepted", "rejected", "requeued"], str]:
        """
        Submits a single flag to the flag checking service. Returns a tuple
        containing the flag's status (accepted, rejected, or requeued)
        and the response message from the service.

        Use this when the flag checking service allows submitting only one flag
        at the time (e.g. over TCP).
        """

        return "accepted", "FLAG_3B37DF144CE4A83566BB OK"

    def teardown(context: Any):
        """
        Gets called during the shutdown process to clean up any resources,
        such as closing the connection and similar.
        """
        pass
    ```


## Examples

The following are complete `submitter.py` scripts from AD competitions Team Serbia previously participated in, which you can freely copy and adjust to suit your needs.


=== "ECSC 2024 Second Demo"

    ```py
    from typing import Literal
    import requests


    def submit(flags: list[str]) -> list[tuple[Literal["accepted", "rejected", "requeued"], str, str]]:
        responses = requests.put(
            "http://10.10.0.1:8080/flags",
            json=flags,
            headers={"X-Team-Token": "518d033ab65f175965de0850b6005628"},
        ).json()

        statuses = {
            "ACCEPTED": "accepted",
            "DENIED": "rejected",
            "RESUBMIT": "requeued",
            "ERROR": "requeued"
        }

        return [
            (
                response["flag"],
                statuses[response["status"]],
                response["msg"],
            )
            for response in responses
        ]
    ```

=== "ENOWARS8 / Compete With Team Czechia 2024"

    ```py
    from typing import Literal
    from pwn import *


    def setup():
        r = remote("10.0.13.37", 1337)
        r.recvuntil(b"\n\n")
        return r


    def submit(flag: str, r) -> tuple[Literal["accepted", "rejected", "requeued"], str]:
        r.sendline(flag.encode())

        response = r.recvline().decode().strip()
        response_flag = response.split(" ")[0]

        if response.endswith("OK"):
            return "accepted", response
        if response.endswith("ERR"):
            return "requeued", response
        else:
            return "rejected", response


    def teardown(r):
        r.close()
    ```


=== "MetaCTF"

    ```py
    from typing import Literal
    import requests


    def submit(flag: str) -> tuple[Literal["accepted", "rejected", "requeued"], str]:
        response = requests.post(
            "http://serbia.metacorp.us:8000/steal", 
            params={
                "token": "a72db0b6c8a8eb73ff77bbbc925074b7",
                "flag": flag
            }
        )

        return "accepted" if "success" in response.text else "rejected", response.text
    ```

## Next steps

After completing your submitter script, in your directory you should have the following:

```
server-workspace/
└── submitter.py
```

Next step is writing the flag ID fetching script.

- [x] [Create an empty directory on your server](./index.md) ✅
- [x] [Write the **submitter** script](./submitter.md) ✅
- [ ] [Write the **flag IDs fetching** script](./flag-ids.md) 👈
- [ ] [Configure the Avala server](./configuration.md)
- [ ] [Launch all containers using Docker Compose](./launching.md)

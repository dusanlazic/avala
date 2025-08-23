# Writing flag IDs fetching script

The same principles apply here as they do for the submitter script. Avala lets you write your own flag ID fetching script tailored to the competition's requirements. This script, written by you, is responsible for fetching the latest flag IDs and converting them to a standardized JSON format. Avala executes this script at the start of every tick and takes care of potential delays, network hiccups and other common issues during AD.

Your flag IDs fetching script must adhere to the template specified below. If you like to learn by examples, you'll find them at the [bottom of the page](#examples).

As a first step, create a file named `flag_ids.py` in your directory.

---

## Script structure

The flag ID fetching script is composed of two main functions: `fetch` and `process`. The `fetch` function is responsible for retrieving raw flag IDs from the game server, while the `process` function standardizes this raw data into a structured format that Avala can work with.

```py
from typing import Any
import requests

def fetch() -> dict | list:
    """
    Fetches raw flag IDs from the game server and returns them as a dictionary.
    Exceptions and retries are handled internally by Avala. It's advisable to
    set a timeout for requests to prevent the server from hanging indefinitely.
    """

    # The actual script from the "Compete With Team Czechia 2024" event.
    # Replace this code with your own.

    return requests.get("http://172.19.1.5:5000/competition/teams.json", timeout=5).json()

def process(raw: dict) -> dict[str, dict[str, list[Any]]]:
    """
    Processes the raw flag IDs returned by fetch function into a standardized, 
    structured format. Flag IDs must be organized by service name and team IP 
    address, and be stored in a list where each item corresponds to the flag
    IDs of a single tick.

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
    """

    # The actual script from the "Compete With Team Czechia 2024" event.
    # Replace this code with your own.

    processed: dict[str, dict[str, list[Any]]] = {}

    for service_name, teams in raw["flag_ids"].items():
        if service_name not in processed:
            processed[service_name] = {}
        for team_num, flag_ids in teams.items():
            processed[service_name][team_ip] = flag_ids

    return processed

```

## Examples

The following are complete `flag_id.py` scripts from AD competitions Team Serbia previously participated in, which you can freely copy and adjust to suit your needs.

=== "CWTC 2024"

    ```py
    import requests
    from typing import Any


    def fetch_json() -> dict:
        return requests.get("http://172.19.1.5:5000/competition/teams.json").json()


    def process_json(raw: dict) -> dict[str, dict[str, list[Any]]]:
        processed: dict[str, dict[str, list[Any]]] = {}

        for service_name, teams in raw["flag_ids"].items():

            if service_name not in processed:
                processed[service_name] = {}
            
            for team_num, flag_ids in teams.items():
                team_ip = f"172.20.{team_num}.5"
                processed[service_name][team_ip] = flag_ids

        return processed
    ```

=== "ENOWARS8"

    ```py
    import requests
    from typing import Any


    def fetch_json() -> dict:
        return requests.get("https://8.enowars.com/scoreboard/attack.json").json()


    def process_json(raw: dict) -> dict[str, dict[str, list[Any]]]:
        processed: dict[str, dict[str, list[Any]]] = {}

        for service_name, teams in raw["services"].items():
            
            if service_name not in processed:
                processed[service_name] = {}

            for team_ip, flag_ids in teams.items():
                processed[service_name][team_ip] = flag_ids

        return processed
    ```

=== "MetaCTF"

    ```py
    import requests
    from typing import Any


    def fetch_json() -> dict:
        return requests.get("http://serbia.metacorp.us:8000/flagids").json()


    def process_json(raw: dict) -> dict[str, dict[str, list[Any]]]:
        processed: dict[str, dict[str, list[Any]]] = {}

        for entry in raw:
            service_name = entry["service"]
            service_id = entry["service_id"]
            team_id = entry["team_id"]
            flag_id = entry["flag_id"]
            
            team_ip = "10.100.%s.%s" % (team_id, service_id)

            if service_name not in processed:
                processed[service_name] = {}
            
            if team_ip not in processed[service_name]:
                processed[service_name][team_ip] = []

            processed[service_name][team_ip].insert(0, flag_id)

        return processed
    ```

=== "ECSC 2024 Demo"

    ```py
    import requests
    from typing import Any
    from concurrent.futures import ThreadPoolExecutor, as_completed


    def fetch_json() -> dict | list:
        root = requests.get("http://10.10.0.1:8081/").json()
        response = {}

        teams = root["teams"]
        services = root["services"]
        rounds = [str(round) for round in root["rounds"]]

        # Build structure

        for service in services:
            service_shortname = service["shortname"]

            if service_shortname not in response:
                response[service_shortname] = {}

            for team in teams:
                team_id = str(team["id"])
                team_ip = f"10.60.{team_id}.1"

                if team_ip not in response[service_shortname]:
                    response[service_shortname][team_ip] = []

        # Fetch flag IDs
        
        def fetch_flag_id(service_shortname, team_id, round):
            flag_id = requests.get("http://10.10.0.1:8081/flagIds", params={
                "service": service_shortname,
                "team": team_id,
                "round": round
            }).json()
            try:
                value = flag_id[service_shortname][team_id][round]
            except KeyError:
                return service_shortname, team_id, None
            return service_shortname, team_id, value

        # Run in threads since there's too many requests

        with ThreadPoolExecutor(max_workers=128) as executor:
            futures = []
            for service in services:
                service_shortname = service["shortname"]
                for team in teams:
                    team_id = str(team["id"])
                    for round in rounds:
                        futures.append(executor.submit(fetch_flag_id, service_shortname, team_id, round))

            for future in as_completed(futures):
                service_shortname, team_id, value = future.result()
                if value:
                    team_ip = f"10.60.{team_id}.1"
                    response[service_shortname][team_ip].append(value)

        return response


    def process_json(raw: dict) -> dict[str, dict[str, list[Any]]]:
        return raw
    ```

## Next steps

After completing your flag IDs fetching script, in your directory you should have the following:

```
server-workspace/
├── flag_ids.py
└── submitter.py
```

Next step is writing the flag ID fetching script.

- [x] [Create an empty directory on your server](./index.md) ✅
- [x] [Write the **submitter** script](./submitter.md) ✅
- [x] [Write the **flag IDs fetching** script](./flag-ids.md) ✅
- [ ] [Configure the Avala server](./configuration.md) 👈
- [ ] [Launch all containers using Docker Compose](./launching.md)

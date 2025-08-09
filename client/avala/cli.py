import json
import os

import click

from .main import DOT_DIR_PATH, Avala

CONFIG_FILE_PATH = DOT_DIR_PATH / "config.json"


def setup_client() -> Avala:
    """
    Sets up and returns an instance of the Avala client based on the configuration file.

    :return: An instance of the Avala client.
    :rtype: Avala
    """
    if not CONFIG_FILE_PATH.exists():
        click.echo("Configuration file not found. Please run 'avala init' to create one.")
        exit(1)

    with open(CONFIG_FILE_PATH, "r") as file:
        config = json.load(file)

    avala = Avala(
        host=config["host"],
        port=config["port"],
        name=config["name"],
        password=config.get("password"),
        redis_url=config.get("redis_url"),
    )

    for directory in config.get("exploit_directories", []):
        avala.register_directory(directory)

    return avala


@click.group()
def cli():
    pass


@cli.command()
@click.argument("exploit_alias")
def run(exploit_alias: str):
    avala = setup_client()
    avala.run_exploit(exploit_alias)


@cli.command()
def init():
    host: str = click.prompt("Server host", type=str, default="localhost", show_default=True)
    port: int = click.prompt("Server port", type=int, default=2024, show_default=True)
    name: str = click.prompt("Username", type=str, default="anon", show_default=True)
    password: str | None = click.prompt(
        "Password (if required)", type=str, hide_input=True, default="", show_default=True
    )
    redis_url: str | None = click.prompt("Server Redis URL (optional)", type=str, default="", show_default=True)

    main_py_content = f"""
from avala import Avala

avl = Avala(
    host="{host}",
    port={port},
    name="{name}",
    {"# " if not password else ""}password="{password}",
    {"# " if not redis_url else ""}redis_url="{redis_url}"
)

avl.register_directory("exploits")

avl.start()
"""

    with open("main.py", "w") as f:
        f.write(main_py_content)

    if not os.path.exists("exploits"):
        os.makedirs("exploits", exist_ok=True)

    config = {
        "host": host,
        "port": port,
        "name": name,
        "password": password if password else None,
        "redis_url": redis_url if redis_url else None,
        "exploit_directories": ["exploits"],
    }

    if not DOT_DIR_PATH.exists():
        DOT_DIR_PATH.mkdir(exist_ok=True)

    with open(CONFIG_FILE_PATH, "w") as file:
        json.dump(config, file)

    click.echo("🚀 Initialization complete. Run 'python main.py' to start Avala.")

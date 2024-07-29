import yaml
from addict import Dict
from pathlib import Path
from .shared.logs import logger
from .shared.validation import validate_data
from .validation.schemas import client_yaml_schema

DOT_DIR_PATH = Path(".avala")

config = Dict(
    {
        "connect": {
            "protocol": "http",
            "host": "localhost",
            "port": 2024,
            "username": "anon",
        },
    }
)


def load_user_config():
    # Remove datetime resolver
    # https://stackoverflow.com/a/52312810
    yaml.SafeLoader.yaml_implicit_resolvers = {
        k: [r for r in v if r[0] != "tag:yaml.org,2002:timestamp"]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    for ext in ["yml", "yaml"]:
        if Path(f"avala.{ext}").is_file():
            with open(f"avala.{ext}", "r") as file:
                user_config = yaml.safe_load(file)
                if not user_config:
                    logger.error(f"No configuration found in avala.{ext}. Exiting...")
                    exit(1)
                break
    else:
        logger.error(
            "avala.yaml/.yml not found in the current working directory. Exiting..."
        )
        exit(1)

    if not validate_data(user_config, client_yaml_schema):
        logger.error("Fix errors in avala.yaml and rerun.")
        exit(1)

    config.update(user_config)

    logger.info("Loaded user configuration.")

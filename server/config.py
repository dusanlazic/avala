import yaml
from addict import Dict
from pathlib import Path
from shared.logs import logger
from shared.validation import validate_data
from .validation.custom import validate_delay, validate_interval
from .validation.schemas import server_yaml_schema

DOT_DIR_PATH = Path(".fast")
STATE_FILE_PATH = DOT_DIR_PATH / "state.json"

config = Dict(
    {
        "game": {},
        "submitter": {"module": "submitter"},
        "server": {"host": "0.0.0.0", "port": 2023},
        "database": {
            "name": "fastdb",
            "user": "admin",
            "password": "admin",
            "host": "localhost",
            "port": 5432,
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
        if Path(f"server.{ext}").is_file():
            with open(f"server.{ext}", "r") as file:
                user_config = yaml.safe_load(file)
                if not user_config:
                    logger.error(f"No configuration found in server.{ext}. Exiting...")
                    exit(1)
                break
    else:
        logger.error(
            "server.yaml not found in the current working directory. Exiting..."
        )
        exit(1)

    if not validate_data(
        user_config, server_yaml_schema, custom=[validate_delay, validate_interval]
    ):
        logger.error("Fix errors in server.yaml and rerun.")
        exit(1)

    config.update(user_config)

    # Wrap single team ip in a list
    if type(config.game.team_ip) != list:
        config.game.team_ip = [config.game.team_ip]

    logger.info("Loaded user configuration.")

import requests
from addict import Dict
from shared.logs import logger
from .config import config


class APIClient:
    def __init__(self) -> None:
        self.conn_str: str = None
        self.game: Dict = None
        self.schedule: Dict = None

    def connect(self):
        if config.connect.password:
            conn_str = "%s://%s:%s@%s:%s" % (
                config.connect.protocol,
                config.connect.username,
                config.connect.password,
                config.connect.host,
                config.connect.port,
            )
        else:
            conn_str = "%s://%s:%s" % (
                config.connect.protocol,
                config.connect.host,
                config.connect.port,
            )

        logger.info(
            "Connecting to <blue>%s</blue>"
            % conn_str.replace(":" + config.connect.password + "@", ":*****@")
        )

        try:
            requests.get(f"{conn_str}/connect/health").raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to connect to the server: %s" % e)
            if e.response and e.response.status_code == 401:
                logger.error(
                    "Note: Invalid credentials. Check the password with your teammates."
                )
            exit(1)

        logger.info("Fetching game information...")

        try:
            self.params = Dict(requests.get(f"{conn_str}/connect/game").json())
        except Exception as e:
            logger.error("Failed to fetch game information: %s" % e)
            exit(1)

        try:
            self.schedule = Dict(requests.get(f"{conn_str}/connect/schedule").json())
        except Exception as e:
            logger.error("Failed to fetch scheduling information: %s" % e)
            exit(1)

        logger.info("Connected successfully.")


client = APIClient()

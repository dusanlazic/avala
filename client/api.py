import json
import requests
from addict import Dict
from shared.logs import logger
from shared.util import colorize
from .config import config, DOT_DIR_PATH


class APIClient:
    def __init__(self) -> None:
        self.conn_str: str = None
        self.game: Dict = None
        self.schedule: Dict = None

    def connect(self):
        """Connect to the server and fetch game information."""

        if config.connect.password:
            self.conn_str = "%s://%s:%s@%s:%s" % (
                config.connect.protocol,
                config.connect.username,
                config.connect.password,
                config.connect.host,
                config.connect.port,
            )
        else:
            self.conn_str = "%s://%s:%s" % (
                config.connect.protocol,
                config.connect.host,
                config.connect.port,
            )

        logger.info(
            "Connecting to <blue>%s</blue>"
            % self.conn_str.replace(":" + config.connect.password + "@", ":*****@")
        )

        try:
            requests.get(f"{self.conn_str}/connect/health").raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to connect to the server: %s" % e)
            if e.response and e.response.status_code == 401:
                logger.error(
                    "Note: Invalid credentials. Check the password with your teammates."
                )
            exit(1)

        logger.info("Fetching game information...")

        try:
            self.game = Dict(requests.get(f"{self.conn_str}/connect/game").json())
        except Exception as e:
            logger.error("Failed to fetch game information: %s" % e)
            exit(1)

        try:
            self.schedule = Dict(
                requests.get(f"{self.conn_str}/connect/schedule").json()
            )
        except Exception as e:
            logger.error("Failed to fetch scheduling information: %s" % e)
            exit(1)

        logger.info("Connected successfully.")

    def export_settings(self):
        """Export the API client settings to a JSON file so executors can reuse it."""
        with open(DOT_DIR_PATH / "api_client.json", "w") as file:
            json.dump(
                {
                    "conn_str": self.conn_str,
                    "game": self.game,
                    "schedule": self.schedule,
                },
                file,
            )

    def import_settings(self):
        """Import the API client settings from a JSON file instead of calling connect().
        Used when running executors.
        """
        with open(DOT_DIR_PATH / "api_client.json", "r") as file:
            data = Dict(json.load(file))
            self.conn_str = data.conn_str
            self.game = data.game
            self.schedule = data.schedule

    def enqueue(self, flags, exploit_name, target):
        enqueue_body = {
            "values": flags,
            "exploit": exploit_name,
            "target": target,
        }

        try:
            response = requests.post(f"{self.conn_str}/flags/queue", json=enqueue_body)
            response.raise_for_status()

            data = response.json()
            logger.info(
                "✅ Enqueued <bold>%d/%d</> flags from <bold>%s</> via <bold>%s</>."
                % (
                    data["enqueued"],
                    len(flags),
                    colorize(target),
                    colorize(exploit_name),
                )
            )
        except Exception as e:
            logger.error(
                "Failed to enqueue flags from <bold>%s</> via <bold>%s</>: %s"
                % (
                    target,
                    exploit_name,
                    e,
                )
            )
            # TODO: Backup flags somewhere
            # maybe even push them directlry to rabbitmq


client = APIClient()
import json
import requests
from addict import Dict
from .shared.logs import logger
from .shared.util import colorize
from .config import ConnectionConfig, DOT_DIR_PATH
from .models import UnscopedAttackData


class APIClient:
    def __init__(self, config: ConnectionConfig = None) -> None:
        self.config: ConnectionConfig | None = config

        self.conn_str: str = None
        self.game: Dict = None
        self.schedule: Dict = None

    def connect(self):
        """Connect to the server and fetch game information."""

        if self.config.password:
            self.conn_str = "%s://%s:%s@%s:%s" % (
                self.config.protocol,
                self.config.username,
                self.config.password,
                self.config.host,
                self.config.port,
            )
        else:
            self.conn_str = "%s://%s:%s" % (
                self.config.protocol,
                self.config.host,
                self.config.port,
            )

        logger.info(
            "Connecting to <blue>%s</blue>"
            % self.conn_str.replace(":" + self.config.password + "@", ":*****@")
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

    def heartbeat(self):
        if not self.conn_str:
            raise RuntimeError("Not connected to the server.")

        requests.get(f"{self.conn_str}/connect/health").raise_for_status()

    def export_settings(self):
        """Export the API client settings to a JSON file so executors can reuse it."""
        DOT_DIR_PATH.mkdir(exist_ok=True)

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
        Used when running executors or running client in workshop mode.
        """
        with open(DOT_DIR_PATH / "api_client.json", "r") as file:
            data = Dict(json.load(file))
            self.conn_str = data.conn_str
            self.game = data.game
            self.schedule = data.schedule

    def enqueue(self, flags: list[str], exploit_alias: str, target: str):
        enqueue_body = {
            "values": flags,
            "exploit": exploit_alias,
            "target": target,
        }

        response = requests.post(f"{self.conn_str}/flags/queue", json=enqueue_body)
        response.raise_for_status()

        data = response.json()
        logger.info(
            "✅ Enqueued <bold>%d/%d</> flags from <bold>%s</> via <bold>%s</>."
            % (
                data["enqueued"],
                len(flags),
                colorize(target),
                colorize(exploit_alias),
            )
        )

    def wait_for_attack_data(self) -> UnscopedAttackData:
        try:
            response = requests.get(f"{self.conn_str}/attack_data/subscribe")
            response.raise_for_status()
            self._cache_attack_data(response.json())

            return UnscopedAttackData(response.json())
        except:
            return self._get_cached_attack_data()

    def get_attack_data(self) -> UnscopedAttackData:
        try:
            response = requests.get(f"{self.conn_str}/attack_data/current")
            response.raise_for_status()
            self._cache_attack_data(response.json())

            return UnscopedAttackData(response.json())
        except:
            return self._get_cached_attack_data()

    def _cache_attack_data(self, response_json) -> None:
        with open(DOT_DIR_PATH / "cached_attack_data.json", "w") as file:
            json.dump(response_json, file)

    def _get_cached_attack_data(self) -> UnscopedAttackData:
        logger.warning("Failed to fetch attack data. Using cached attack data instead.")
        with open(DOT_DIR_PATH / "cached_attack_data.json") as file:
            return UnscopedAttackData(json.load(file))

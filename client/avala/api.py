import json
import requests
from addict import Dict
from .shared.logs import logger
from .shared.util import colorize
from .config import ConnectionConfig, DOT_DIR_PATH
from .models import UnscopedAttackData


class APIClient:
    """
    Class for interacting with the Avala API server and keeping configuration for the game and scheduling.
    """

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
            "Connecting to <blue>{conn}</blue>",
            conn=self.conn_str.replace(":" + self.config.password + "@", ":*****@"),
        )

        try:
            requests.get(f"{self.conn_str}/connect/health").raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to connect to the server: {error}", error=e)
            if e.response and e.response.status_code == 401:
                logger.error(
                    "Note: Invalid credentials. Check the password with your teammates."
                )
            raise

        logger.info("Fetching game information...")

        # Fetch information about the game (e.g. flag format, team IP, etc.)
        try:
            self.game = Dict(requests.get(f"{self.conn_str}/connect/game").json())
        except Exception as e:
            logger.error("Failed to fetch game information: {error}", error=e)
            raise

        # Fetch information needed for synchronizing client with the server.
        try:
            self.schedule = Dict(
                requests.get(f"{self.conn_str}/connect/schedule").json()
            )
        except Exception as e:
            logger.error("Failed to fetch scheduling information: {error}", error=e)
            raise

        logger.info("Connected successfully.")

    def heartbeat(self):
        """
        Check if the client is still connected to the server.

        :raises RuntimeError: If the connection was never established.
        """
        if not self.conn_str:
            raise RuntimeError("Not connected to the server.")

        requests.get(f"{self.conn_str}/connect/health").raise_for_status()

    def export_settings(self):
        """Exports fetched API client settings to a JSON file so executors and workshop
        mode can access them without reconnecting."""
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
        """Imports API client settings from a JSON file instead of reconnecting.
        Used by runners or client when launched in workshop mode.
        """
        if not (DOT_DIR_PATH / "api_client.json").exists():
            raise FileNotFoundError()

        with open(DOT_DIR_PATH / "api_client.json", "r") as file:
            data = Dict(json.load(file))
            self.conn_str = data.conn_str
            self.game = data.game
            self.schedule = data.schedule

    def enqueue(self, flags: list[str], exploit_alias: str, target: str):
        """
        Sends flags to the server for enqueuing and duplicate filtering.

        :param flags: List of flags to enqueue.
        :type flags: list[str]
        :param exploit_alias: Alias of the exploit that retrieved the flags.
        :type exploit_alias: str
        :param target: IP address or hostname of the target/victim team.
        :type target: str
        """
        enqueue_body = {
            "values": flags,
            "exploit": exploit_alias,
            "target": target,
        }

        response = requests.post(f"{self.conn_str}/flags/queue", json=enqueue_body)
        response.raise_for_status()

        data = response.json()
        logger.info(
            "{icon} Enqueued <b>{enqueued}/{total}</> flags from <b>{target}</> via <b>{exploit}</>.",
            icon="✅" if data["enqueued"] else "❗",
            enqueued=data["enqueued"],
            total=len(flags),
            target=colorize(target),
            exploit=colorize(exploit_alias),
        )

    def wait_for_attack_data(self) -> UnscopedAttackData:
        """
        Fetches the latest attack data from the server by long polling.
        Useful for starting the attacks using the latest up-to-date attack data.

        :return: Unscoped attack data covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedAttackData
        """
        try:
            response = requests.get(f"{self.conn_str}/attack-data/subscribe")
            response.raise_for_status()

            if response.status_code == 200:
                self._cache_attack_data(response.json())

            return UnscopedAttackData(response.json())
        except:
            return self._get_cached_attack_data()

    def get_attack_data(self) -> UnscopedAttackData:
        """
        Fetches the current available attack data from the server.
        Useful for starting the attacks immediately using the currently available attack data.

        :return: Unscoped attack data covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedAttackData
        """
        try:
            response = requests.get(f"{self.conn_str}/attack-data/current")
            response.raise_for_status()

            if response.status_code == 200:
                self._cache_attack_data(response.json())

            return UnscopedAttackData(response.json())
        except:
            return self._get_cached_attack_data()

    def _cache_attack_data(self, response_json: dict) -> None:
        """
        Caches the fetched attack data to a JSON file as a temporary fallback in case of
        connection loss or server downtime.

        :param response_json: Dictionary containing the fetched attack data.
        :type response_json: dict
        """
        with open(DOT_DIR_PATH / "cached_attack_data.json", "w") as file:
            json.dump(response_json, file)

    def _get_cached_attack_data(self) -> UnscopedAttackData:
        """
        Uses the cached attack data as a fallback in case of connection loss or server downtime.

        :raises FileNotFoundError: Attack data was never fetched.
        :raises RuntimeError: Attack data is corrupted or was never fetched.
        :return: Unscoped attack data covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedAttackData
        """
        logger.warning("Failed to fetch attack data. Using cached attack data instead.")

        if not (DOT_DIR_PATH / "cached_attack_data.json").exists():
            raise FileNotFoundError("Attack data was never fetched.")

        with open(DOT_DIR_PATH / "cached_attack_data.json") as file:
            try:
                return UnscopedAttackData(json.load(file))
            except:
                raise RuntimeError("Attack data is corrupted or was never fetched.")

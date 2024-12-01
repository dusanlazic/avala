import json
from pathlib import Path

import httpx

from ..logging import colorize, logger
from .schemas import (
    CachedConfig,
    ConnectionConfig,
    GameConfig,
    ScheduleConfig,
    UnscopedAttackData,
)

DOT_DIR_PATH = Path(".avala")


class APIClient:
    """
    Class for interacting with the Avala server API and keeping configuration for the game and scheduling.
    """

    def __init__(
        self,
        connection: ConnectionConfig,
        *,
        game: GameConfig | None = None,
        schedule: ScheduleConfig | None = None,
    ) -> None:
        self.connection: ConnectionConfig = connection
        self.client: httpx.Client = self._setup_http_client()
        self.game: GameConfig = game or self._fetch_game_settings()
        self.schedule: ScheduleConfig = schedule or self._fetch_schedule_settings()

    @classmethod
    def connect(cls, connection: ConnectionConfig) -> "APIClient":
        try:
            return cls(connection)
        except Exception as e:
            logger.error("Failed to connect to the server: {error}", error=e)
            raise

    @classmethod
    def reuse(cls) -> "APIClient":
        if not (DOT_DIR_PATH / "api_client.json").exists():
            raise FileNotFoundError()

        try:
            with open(DOT_DIR_PATH / "api_client.json", "r") as file:
                data = json.load(file)

            cached_config = CachedConfig(**data)
        except Exception as e:
            logger.error("Failed to load cached settings: {error}", error=e)
            raise

        return cls(
            connection=cached_config.connection,
            game=cached_config.game,
            schedule=cached_config.schedule,
        )

    @classmethod
    def connect_first(cls, connection: ConnectionConfig) -> "APIClient":
        try:
            return cls.connect(connection)
        except Exception:
            return cls.reuse()

    @classmethod
    def reuse_first(cls, connection: ConnectionConfig) -> "APIClient":
        try:
            return cls.reuse()
        except Exception:
            return cls.connect(connection)

    def cache_settings(self):
        """Exports settings fetched from the API to a local file so they can be reused when
        instancing the APIClient using `APIClient.reuse()`."""
        DOT_DIR_PATH.mkdir(exist_ok=True)

        with open(DOT_DIR_PATH / "api_client.json", "w") as file:
            json_data = CachedConfig(
                connection=self.connection, game=self.game, schedule=self.schedule
            ).model_dump_json()
            file.write(json_data)

    def heartbeat(self) -> None:
        """
        Check if the client is still connected to the server.

        :raises RuntimeError: If the connection was never established.
        :raises httpx.HTTPStatusError: If the server is unreachable within 10 seconds or responds with an error status code.
        """
        self.client.get(f"/connect/health", timeout=10).raise_for_status()

    def enqueue(self, flags: list[str], exploit_alias: str, target: str) -> None:
        """
        Sends flags to the server for enqueuing and duplicate filtering.

        :param flags: List of flags to enqueue.
        :type flags: list[str]
        :param exploit_alias: Alias of the exploit that retrieved the flags.
        :type exploit_alias: str
        :param target: IP address or hostname of the target/victim team.
        :type target: str
        :raises httpx.HTTPStatusError: If the server responds with an error status code.
        """
        enqueue_body = {
            "values": flags,
            "exploit": exploit_alias,
            "target": target,
        }

        response = self.client.post("/flags/queue", json=enqueue_body)
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
        Fetches and waits for the latest attack data from the server by long polling.
        Useful for starting the attacks using the latest up-to-date attack data.

        :raises httpx.HTTPStatusError: If the server responds with an error status code.
        :return: Unscoped attack data covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedAttackData
        """
        try:
            response = self.client.get("/attack-data/subscribe")
            response.raise_for_status()

            if response.status_code == 200:
                self._cache_attack_data(response.json())

            return UnscopedAttackData(response.json())
        except Exception:
            return self._get_cached_attack_data()

    def get_attack_data(self) -> UnscopedAttackData:
        """
        Fetches the current available attack data from the server.
        Useful for starting the attacks immediately using the currently available attack data.

        :raises httpx.HTTPStatusError: If the server responds with an error status code.
        :return: Unscoped attack data covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedAttackData
        """
        try:
            response = self.client.get("/attack-data/current")
            response.raise_for_status()

            if response.status_code == 200:
                self._cache_attack_data(response.json())

            return UnscopedAttackData(response.json())
        except Exception:
            return self._get_cached_attack_data()

    def _setup_http_client(self) -> httpx.Client:
        """
        Sets up the HTTP client for interacting with the Avala API server.

        :raises ConnectionError: If the client fails to establish a connection to the server.
        :return: HTTP client configured for interacting with the server.
        :rtype: httpx.Client
        """
        auth = (
            httpx.BasicAuth(self.connection.username, self.connection.password)
            if self.connection.password
            else None
        )

        client = httpx.Client(
            auth=auth,
            base_url=f"{self.connection.protocol}://{self.connection.host}:{self.connection.port}",
        )
        try:
            client.get("/connect/health", timeout=10).raise_for_status()
        except Exception as e:
            logger.error("Failed to establish connection: {error}", error=e)
            raise

        return client

    def _fetch_game_settings(self) -> GameConfig:
        try:
            return GameConfig.model_validate(self.client.get("/connect/game").json())
        except Exception as e:
            logger.error("Failed to fetch game information: {error}", error=e)
            raise

    def _fetch_schedule_settings(self) -> ScheduleConfig:
        try:
            return ScheduleConfig.model_validate(
                self.client.get("/connect/schedule").json()
            )
        except Exception as e:
            logger.error("Failed to fetch scheduling information: {error}", error=e)
            raise

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
            except Exception:
                raise RuntimeError("Attack data is corrupted or was never fetched.")

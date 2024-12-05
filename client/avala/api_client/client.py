import json
from pathlib import Path

import httpx

from ..logging import colorize, logger
from .schemas import (
    CachedConfig,
    ConnectionConfig,
    EnqueueBody,
    FlagEnqueueResponse,
    GameConfig,
    ScheduleConfig,
    UnscopedFlagIds,
)

DOT_DIR_PATH = Path(".avala")


class APIClient:
    """
    Class for interacting with the Avala server API and keeping configuration for the
    game and scheduling.
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
        """Exports settings fetched from the API to a local file so they can be reused
        when instancing the APIClient using `APIClient.reuse()`."""
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
        :raises httpx.HTTPStatusError: If the server is unreachable within 10 seconds or
        responds with an error status code.
        """
        self.client.get("/connect/health", timeout=10).raise_for_status()

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
        enqueue_body = EnqueueBody(
            values=flags,
            exploit=exploit_alias,
            target=target,
        )

        response = self.client.post(
            "/flags/queue",
            json=enqueue_body.model_dump(mode="json"),
        )
        response.raise_for_status()

        flag_enqueue_response = FlagEnqueueResponse(**response.json())

        logger.info(
            "{icon} Enqueued <b>{enqueued}/{total}</> flags from <b>{target}</> via <b>{exploit}</>.",
            icon="✅" if flag_enqueue_response.enqueued else "❗",
            enqueued=flag_enqueue_response.enqueued,
            total=len(flags),
            target=colorize(target),
            exploit=colorize(exploit_alias),
        )

    def wait_for_flag_ids(self) -> UnscopedFlagIds:
        """
        Waits for the latest flag ids from the server by long polling. Useful for starting
        the attacks using the latest up-to-date flag ids.

        :raises httpx.HTTPStatusError: If the server responds with an error status code.
        :return: Unscoped flag ids covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedFlagIds
        """
        try:
            response = self.client.get("/attack-data/subscribe")
            response.raise_for_status()

            if response.status_code == 200:
                self._cache_flag_ids(response.json())

            return UnscopedFlagIds(response.json())
        except Exception as e:
            logger.error("Failed to fetch flag ids: {error}", error=e)
            return self._get_cached_flag_ids()

    def fetch_flag_ids(self) -> UnscopedFlagIds:
        """
        Fetches the current available flag IDs from the server.
        Useful for starting the attacks immediately using the currently available flag
        IDs.

        :raises httpx.HTTPStatusError: If the server responds with an error status code.
        :return: Flag ids for all targets across all services, covering the last N ticks
        as provided by the game server.
        :rtype: UnscopedFlagIds
        """
        try:
            response = self.client.get("/attack-data/current")
            response.raise_for_status()

            if response.status_code == 200:
                self._cache_flag_ids(response.json())

            return UnscopedFlagIds(response.json())
        except Exception as e:
            logger.error("Failed to fetch flag ids: {error}", error=e)
            return self._get_cached_flag_ids()

    def _setup_http_client(self) -> httpx.Client:
        """
        Sets up the HTTP client for interacting with the Avala API server.

        :raises ConnectionError: If the client fails to establish a connection to the server.
        :return: HTTP client configured for interacting with the server.
        :rtype: httpx.Client
        """
        auth = httpx.BasicAuth(self.connection.username, self.connection.password) if self.connection.password else None

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
            return ScheduleConfig.model_validate(self.client.get("/connect/schedule").json())
        except Exception as e:
            logger.error("Failed to fetch scheduling information: {error}", error=e)
            raise

    def _cache_flag_ids(self, response_json: dict) -> None:
        """
        Caches the fetched flag IDs to a JSON file as a temporary fallback in case of
        connection loss or server downtime.

        :param response_json: Dictionary containing the fetched flag IDs.
        :type response_json: dict
        """
        with open(DOT_DIR_PATH / "cached_flag_ids.json", "w") as file:
            json.dump(response_json, file)

    def _get_cached_flag_ids(self) -> UnscopedFlagIds:
        """
        Uses the cached flag IDs as a fallback in case of connection loss or server
        downtime.

        :raises FileNotFoundError: Flag IDs were never fetched.
        :raises RuntimeError: Flag IDs are corrupted or were never fetched.
        :return: Unscoped flag IDs covering flag IDs from all services, targets and
        ticks.
        :rtype: UnscopedFlagIds
        """
        logger.warning("Using cached flag IDs instead.")

        if not (DOT_DIR_PATH / "cached_flag_ids.json").exists():
            raise FileNotFoundError("Flag IDs were never fetched.")

        with open(DOT_DIR_PATH / "cached_flag_ids.json") as file:
            try:
                return UnscopedFlagIds(json.load(file))
            except Exception as e:
                raise RuntimeError("Flag IDs are corrupted or were never fetched.") from e

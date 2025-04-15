import json
from pathlib import Path
from typing import Iterable

import httpx

from ..logging import colorize, logger, truncate
from .schemas import (
    ConnectionConfig,
    FlagsEnqueueBody,
    FlagsEnqueueResponse,
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
    ) -> None:
        self.connection: ConnectionConfig = connection
        self.client: httpx.Client = self._setup_http_client()
        self.game: GameConfig
        self.schedule: ScheduleConfig
        self.game, self.schedule = self._fetch_settings()
        DOT_DIR_PATH.mkdir(exist_ok=True)

    @classmethod
    def connect_or_exit(cls, connection: ConnectionConfig) -> "APIClient":
        try:
            return cls(connection)
        except Exception as e:
            logger.error(
                "Failed to connect to Avala server.\n\n<b>{error}</>\n{error_msg}\n",
                error=type(e).__name__,
                error_msg=e,
            )
            logger.info("❌ Exiting...")
            exit(1)

    def heartbeat(self) -> None:
        """
        Check if the client is still connected to the server.

        :raises RuntimeError: If the connection was never established.
        :raises httpx.HTTPStatusError: If the server is unreachable within 5 seconds or
        responds with an error status code.
        """
        self.client.get("/health", timeout=5).raise_for_status()

    def enqueue(
        self,
        flags: Iterable[str],
        host: str,
        worker_name: str,
        service_name: str | None = None,
        exploit_alias: str | None = None,
    ) -> None:
        """
        Sends flags to the server for submission.

        :param flags: Flags to enqueue.
        :type flags: Iterable[str]
        :param host: Host of the target/victim team.
        :type host: str
        :param worker_name: Name of the worker that retrieved the flags.
        :type worker_name: str
        :param service_name: Name of the attacked service.
        :type service_name: str
        :param exploit_alias: Alias of the exploit that retrieved the flags.
        :type exploit_alias: str
        :raises httpx.HTTPStatusError: If the server responds with an error status code.
        """
        enqueue_body = FlagsEnqueueBody(
            values=flags,
            host=host,
            service=service_name,
            worker=worker_name,
            exploit=exploit_alias,
        )

        response = self.client.post(
            "/flags",
            json=enqueue_body.model_dump(mode="json"),
        )
        response.raise_for_status()

        flag_enqueue_response = FlagsEnqueueResponse(**response.json())

        logger.info(
            "{icon} Enqueued <b>{enqueued}/{total}</> flags from <b>{host}</> via <b>{exploit}</>. <d>{flags}</>",
            icon="🚩" if flag_enqueue_response.enqueued else "❗",
            enqueued=flag_enqueue_response.enqueued,
            total=len(flags),
            host=colorize(host),
            exploit=colorize(exploit_alias),
            flags=truncate(", ".join(flags)),
        )

    def wait_for_flag_ids(self) -> UnscopedFlagIds:
        """
        Waits for the latest flag ids from the server by long polling. Useful for starting
        the attacks using the latest up-to-date flag ids.

        :raises httpx.HTTPStatusError: If the server responds with an error status code.
        :return: Unscoped flag ids covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedFlagIds
        """
        response = self.client.get("/flag-ids/subscribe", timeout=self.schedule.tick_duration.total_seconds())
        response.raise_for_status()

        if response.status_code == 200:
            self._cache_flag_ids(response.json())

        return UnscopedFlagIds(response.json())

    def fetch_flag_ids(self) -> UnscopedFlagIds:
        """
        Fetches the current available flag IDs from the server. Useful for starting the attacks immediately using the
        currently available flag IDs.

        :raises httpx.HTTPStatusError: If the server responds with an error status code.
        :return: Flag ids for all targets across all services, covering the last N ticks
        as provided by the game server.
        :rtype: UnscopedFlagIds
        """
        response = self.client.get("/flag-ids/current")
        response.raise_for_status()

        if response.status_code == 200:
            self._cache_flag_ids(response.json())

        return UnscopedFlagIds(response.json())

    def get_cached_flag_ids(self) -> UnscopedFlagIds:
        """
        Uses the cached flag IDs as a fallback in case of connection loss or server downtime.

        :raises FileNotFoundError: Flag IDs were never fetched.
        :raises RuntimeError: Flag IDs are corrupted or were never fetched.
        :return: Unscoped flag IDs covering flag IDs from all services, targets and
        ticks.
        :rtype: UnscopedFlagIds
        """
        logger.warning("⚠️  Using cached flag IDs.")

        if not (DOT_DIR_PATH / "cached_flag_ids.json").exists():
            raise FileNotFoundError("Flag IDs were never fetched.")

        with open(DOT_DIR_PATH / "cached_flag_ids.json") as file:
            return UnscopedFlagIds(json.load(file))

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
        client.get("/health", timeout=5).raise_for_status()

        return client

    def _fetch_settings(self) -> tuple[GameConfig, ScheduleConfig]:
        try:
            response = self.client.get("/configure").json()
            game_data = response.get("game", {})
            schedule_data = response.get("schedule", {})
            return (
                GameConfig.model_validate(game_data),
                ScheduleConfig.model_validate(schedule_data),
            )
        except Exception as e:
            logger.error(
                "Failed to fetch and parse configuration.\n\n<b>{error}</>\n{error_msg}\n",
                error=type(e).__name__,
                error_msg=e,
            )
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

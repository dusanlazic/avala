import concurrent.futures
import importlib.util
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

import tzlocal
from apscheduler.schedulers.background import BlockingScheduler
from pydantic import AwareDatetime

from .api_client import APIClient, ConnectionConfig, UnscopedFlagIds
from .decorator import Batching
from .exploit import Exploit
from .logging import logger
from .storage import BlobStorage


class Avala:
    def __init__(
        self,
        protocol: Literal["http", "https"] = "http",
        host: str = "localhost",
        port: int = 2024,
        username: str = "anon",
        password: str | None = None,
        storage: BlobStorage | None = None,
    ):
        """
        Initializes the Avala client. The client schedules and runs the attacks, extracts and forwards flags to the
        Avala server, and keeps track of the flag IDs to reduce repetition of the same attacks.

        :param protocol: Protocol of the Avala server, defaults to "http"
        :type protocol: Literal[&quot;http&quot;, &quot;https&quot;], optional
        :param host: Host of the Avala server, defaults to "localhost"
        :type host: str, optional
        :param port: Port of the Avala server, defaults to 2024
        :type port: int, optional
        :param username: Player name, defaults to "anon"
        :type username: str, optional
        :param password: Password for the Avala server, defaults to None
        :type password: str | None, optional
        """
        self._connection: ConnectionConfig = ConnectionConfig(
            protocol=protocol,
            host=host,
            port=port,
            username=username,
            password=password,
        )
        self._client: APIClient
        self._scheduler: BlockingScheduler
        self._storage: BlobStorage | None = storage

        self._exploit_directories: list[Path] = []
        self._before_all_hook: Callable | None = None
        self._after_all_hook: Callable | None = None

    def run(self):
        """
        Runs the Avala client in production mode. The client will start scheduling and
        running exploit functions decorated with `@exploit` in the registered
        directories. Call this method after initializing the client and registering the
        exploit directories.
        """
        self._show_banner()
        self._validate_directories()

        self._scheduler = BlockingScheduler()
        self._client = APIClient(self._connection)
        self._client.cache_settings()

        self._scheduler.add_job(
            func=self._schedule_exploits,
            trigger="interval",
            seconds=self._client.schedule.tick_duration,
            id="schedule_exploits",
            next_run_time=self._get_next_tick_start(),
        )

        try:
            self._scheduler.start()
        except KeyboardInterrupt:
            print()  # Add a newline after the ^C
            self._scheduler.shutdown()
            logger.info("Thanks for using Avala!")

    def workshop(self):
        """
        Runs draft exploits (development mode). This method runs exploit functions with `draft = True` in the registered
        directories, helping with the exploit development. This function can be called in a separate process while the
        client is already running in production mode. Call this method after initializing the client and registering
        exploit directories.
        """
        self._validate_directories()

        self._client = APIClient.reuse_first(self._connection)

        try:
            flag_ids = self._client.fetch_flag_ids()
        except (RuntimeError, FileNotFoundError) as e:
            logger.error("{error} aa", error=e)
            exit(1)

        self._run_hook(self._before_all_hook)

        exploits = self._reload_exploits(mode="draft")
        for exploit in exploits:
            exploit.batching = Batching(count=1)
            exploit.setup(game=self._client.game, flag_ids=flag_ids) and exploit.run()

        self._run_hook(self._after_all_hook)

    def fire(self, exploits: list[str]):
        """
        Runs selected exploits immediately, in given order. This function can be called in a separate process while the
        client is already running in production mode. Call this method after initializing the client and registering
        exploit directories.

        :param exploits: Aliases of the exploits to run.
        :type exploits: list[str]
        """
        self._validate_directories()

        self._client = APIClient.reuse_first(self._connection)

        try:
            flag_ids = self._client.fetch_flag_ids()
        except (RuntimeError, FileNotFoundError) as e:
            logger.error("{error} aa", error=e)
            exit(1)

        self._run_hook(self._before_all_hook)

        selected_exploits = (e for e in self._reload_exploits(mode="force") if e.alias in exploits)
        for exploit in selected_exploits:
            exploit.batching = Batching(count=1)
            exploit.setup(game=self._client.game, flag_ids=flag_ids) and exploit.run()

        self._run_hook(self._after_all_hook)

    def register_directory(self, dir_path: str):
        """
        Register a directory containing exploits. The directory path could be either absolute, or relative to your
        **current working directory when running the client**.

        :param dir_path: Path to the directory containing exploits.
        :type dir_path: str
        """
        path = Path(dir_path).resolve()
        if path not in self._exploit_directories:
            self._exploit_directories.append(path)

    def before_all(self):
        """
        Decorator for a function that will be executed before reloading and scheduling attacks, or at the beginning of
        each tick.

        This hook can be used to perform any setup or initialization before running attacks, such as pulling exploits
        from a git repository.
        """

        def decorator(func):
            self._before_all_hook = func
            return func

        return decorator

    def after_all(self):
        """
        Decorator for a function that will be executed after all attacks are completed.

        This hook can be used to perform any cleanup or finalization after running attacks, such as cleaning up
        temporary files, sending a notification, etc.
        """

        def decorator(func):
            self._after_all_hook = func
            return func

        return decorator

    def get_flag_ids(self) -> UnscopedFlagIds:
        """
        Fetches the current available flag ids fetched by the Avala server.

        :return: Unscoped flag ids covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedFlagIds
        """
        return APIClient(self._connection).fetch_flag_ids()

    def get_services(self) -> set[str]:
        """
        Fetches a set of names of the available services in flag ids.

        :return: Set of service names.
        :rtype: set[str]
        """
        return APIClient(self._connection).fetch_flag_ids().get_service_names()

    def submit_flags(
        self,
        flags: list[str],
        exploit_alias: str = "manual",
        target: str = "unknown",
    ) -> None:
        """
        Sends flags to the server for enqueuing and duplicate filtering.

        :param flags: List of flags to enqueue.
        :type flags: list[str]
        :param exploit_alias: Alias of the exploit that retrieved the flags.
        :type exploit_alias: str
        :param target: IP address or hostname of the target/victim team.
        :type target: str
        """
        APIClient(self._connection).enqueue(flags, exploit_alias, target)

    def match_flags(self, output: Any) -> list[str]:
        """
        Matches flags in the output using the flag format defined in the server settings.

        :param output: Any object that may contain flags when converted to a string.
        :type output: Any
        :return: List of flags extracted from the output.
        :rtype: list[str]
        """
        return re.findall(self._client.game.flag_format, str(output))

    def _validate_directories(self):
        """
        Validates and filters out invalid (non-existent) registered exploit directories.
        """
        valid_directories = []
        for path in self._exploit_directories:
            if not path.exists() or not path.is_dir():
                logger.warning("Directory not found: {path}", path=path)
            else:
                valid_directories.append(path)

        logger.info(
            "Registered exploit directories: <green>{directories}</>",
            directories=", ".join([d.name for d in valid_directories]),
        )

        self._exploit_directories = valid_directories

    def _reload_exploits(self, mode: Literal["prod", "draft", "force"]) -> list[Exploit]:
        """
        Reloads exploits, collects their configuration and constructs a list of runnable `Exploit` objects.

        TODO: Update this docstring to reflect the new behavior of the function.

        :param mode: Mode of operation. Can be "prod", "draft", or "force". "Draft" loads only draft exploits, "prod"
        loads only non-draft exploits, and "force" loads all exploits.
        :type mode: Literal[&quot;prod&quot;, &quot;draft&quot;, &quot;force&quot;]
        :param flag_ids: Flag IDs fetched immediately from Avala server. Applicible only with mode "draft" or "force",
        defaults to None.
        :type flag_ids: UnscopedFlagIds | None, optional
        :param flag_ids_future: Future object that results in latest flag IDs when Avala server responds. Applicible
        only with mode "prod", defaults to None.
        :type flag_ids_future: Future[UnscopedFlagIds] | None, optional
        :return: List of `Exploit` objects that can be set up and scheduled.
        :rtype: list[Exploit]
        """

        def patch_pwntools(file_path: Path) -> str:
            """
            Comments out `from pwn import *` to prevent "signal only works in main thread of the main interpreter" error

            :param code: Path to the Python file containing the exploit code.
            :type code: str
            :return: Exploit code without `from pwn import *`
            :rtype: str
            """
            with file_path.open() as file:
                return file.read().replace("from pwn import *\n", "# from pwn import *\n")

        exploits: list[Exploit] = []
        exploit_filepaths = (file for directory in self._exploit_directories for file in directory.glob("*.py"))

        load_all = mode == "force"
        desired_draft_value = mode == "draft"

        for exploit_filepath in exploit_filepaths:
            try:
                spec = importlib.util.spec_from_file_location(exploit_filepath.stem, exploit_filepath.absolute())
                if spec is None:
                    raise Exception("Failed to load module spec.")

                module = importlib.util.module_from_spec(spec)
                patched_code = patch_pwntools(exploit_filepath)
                compiled_code = compile(patched_code, exploit_filepath.absolute(), "exec")
                exec(compiled_code, module.__dict__)
                for _, func in module.__dict__.items():
                    if (
                        callable(func)
                        and hasattr(func, "exploit")
                        and isinstance(func.exploit, Exploit)
                        and (load_all or func.exploit.is_draft == desired_draft_value)
                    ):
                        exploits.append(func.exploit)
            except Exception as e:
                logger.error(
                    "Failed to load exploit from {file}: {error}",
                    file=exploit_filepath,
                    error=e,
                )

        logger.debug("Loaded {count} exploits.", count=len(exploits))
        return exploits

    def _schedule_exploits(self):
        """
        Scheduled job that runs every tick to reload and schedule exploits. This job is also responsible for fetching
        flag_ids and running before_all and after_all
        hooks.
        """
        executor = concurrent.futures.ThreadPoolExecutor()
        flag_ids_future = executor.submit(self._client.wait_for_flag_ids)

        if self._before_all_hook:
            self._before_all_hook()

        now = datetime.now()

        # Sort exploits so that exploits that don't take flag IDs are scheduled first, followed by exploits that do.
        # This way, fetching flag ids (resolving flag_ids_future) won't block scheduling of exploits that don't need
        # flag ids.

        exploits = self._reload_exploits(mode="prod")
        ordered_exploits = [e for e in exploits if not e.takes_flag_ids] + [e for e in exploits if e.takes_flag_ids]

        for exploit in ordered_exploits:
            flag_ids = flag_ids_future.result() if exploit.takes_flag_ids else None
            if not exploit.setup(game=self._client.game, flag_ids=flag_ids):
                continue
            for batch_idx in range(exploit.get_batch_count()):
                self._scheduler.add_job(
                    func=exploit.run,
                    args=[batch_idx],
                    trigger="date",
                    run_date=now + exploit.delay + exploit.get_batch_interval() * batch_idx,
                    misfire_grace_time=None,
                )

        executor.shutdown(wait=True)

        if self._after_all_hook:
            self._after_all_hook()

    def _run_hook(self, func: Callable | None):
        """
        Runs a hook function, catches and logs any exceptions that occur.

        :param func: Hook function to run.
        :type func: Callable
        """
        if func:
            try:
                func()
            except Exception as e:
                logger.error("Error in {function}: {error}", function=func.__name__, error=e)

    def _enqueue_pending_flags(self):
        """
        Job that periodically checks the connection with the server and tries to push
        the pending flags collected during the server downtime.
        """
        try:
            self._client.heartbeat()
        except Exception:
            logger.warning(
                "⚠️ Cannot establish connection with the server. "
                + "<b>{pending_flags}</> flags are waiting to be submitted.",
                pending_flags=(
                    123  # TODO: Get the number of pending flags
                ),
            )
        else:
            results = set()  # TODO: Get pending flags from redis and group them by target and alias

            if results:
                logger.info("Server is back online! Submitting pending flags...")

            for row in results:
                flags = row.flags.split(",")
                self._client.enqueue(flags, row.alias, row.target)
                # TODO: Remove pending flags from redis

    def _get_next_tick_start(self) -> AwareDatetime:
        """
        Calculate the start time of the next tick.
        """
        first_tick_start = self._client.schedule.first_tick_start
        tick_duration = self._client.schedule.tick_duration
        now: AwareDatetime = datetime.now(tzlocal.get_localzone())

        game_has_started = first_tick_start > now

        if not game_has_started:
            return first_tick_start

        return now + tick_duration - (now - first_tick_start) % tick_duration

    def _show_banner(self):
        print(
            """\033[34;1m
      db
     ;MM:
    ,V^MM. 7MM""Yq.  ,6"Yb.  `7M""MMF',6"Yb.
   ,M  `MM `MM   j8 8)   MM    M  MM 8)   MM
   AbmmmqMA MM""Yq.  ,pm9MM   ,P  MM  ,pm9MM
  A'     VML`M   j8 8M   MM . d'  MM 8M   MM
.AMA.   .AMMA.mmm9' `Moo9^Yo8M' .JMML`Moo9^Yo.
\033[0m"""
        )

import concurrent.futures
import importlib.util
import logging
import re
import time
from datetime import datetime
from multiprocessing import Process
from pathlib import Path
from queue import Empty
from typing import Any, Callable, Iterable, Literal

import tzlocal
from apscheduler.schedulers.background import BlockingScheduler
from httpx import HTTPStatusError, RequestError
from pydantic import AwareDatetime, ValidationError
from watchdog.events import FileModifiedEvent
from watchdog.observers import Observer

from .api_client.client import APIClient
from .api_client.schemas import ConnectionConfig, FlagsEnqueueBody, UnscopedFlagIds
from .decorator.schemas import Batching
from .exploit import Exploit
from .logging import colorize, logger, truncate
from .storage.impl import BlobStorage, FlagIdsHashStorage, UnsentFlagStorage
from .watcher import FileEventHandler


class Avala:
    def __init__(
        self,
        protocol: Literal["http", "https"] = "http",
        host: str = "localhost",
        port: int = 2024,
        name: str = "anon",
        password: str | None = None,
        redis_url: str | None = None,
    ) -> None:
        """
        Initializes the Avala client. The client is responsible for scheduling, setting up, and running exploits.
        Besides launching exploits, client also collects and submits flags to the Avala server, and reduces repeating
        the same attacks by keeping track of used flag IDs.

        :param protocol: Protocol used by the Avala server, defaults to "http"
        :type protocol: Literal[&quot;http&quot;, &quot;https&quot;], optional
        :param host: Host of the Avala server, defaults to "localhost"
        :type host: str, optional
        :param port: Port of the Avala server, defaults to 2024
        :type port: int, optional
        :param name: Name used for worker identification, defaults to "anon"
        :type name: str, optional
        :param password: Password to the Avala server, defaults to None
        :type password: str | None, optional
        :param redis_url: Connection URL of Redis storage used for keeping track of flag IDs and for blob storage in
        exploit functions, defaults to None
        :type redis_url: str | None, optional
        """

        self._connection: ConnectionConfig = ConnectionConfig(
            protocol=protocol,
            host=host,
            port=port,
            username=name,
            password=password,
        )
        self._worker_name: str = name
        self._client: APIClient = APIClient(self._connection)
        self._scheduler: BlockingScheduler
        self._blob_storage: BlobStorage | None = BlobStorage(redis_url, "avala_blobs") if redis_url else None
        self._flag_ids_hash_storage: FlagIdsHashStorage | None = (
            FlagIdsHashStorage(redis_url, "avala_flag_hashes") if redis_url else None
        )
        self._unsent_flag_storage: UnsentFlagStorage | None = (
            UnsentFlagStorage(redis_url, "avala_unsent_flags") if redis_url else None
        )

        self._exploit_directories: set[Path] = set()
        self._before_all_hook: Callable | None = None
        self._after_all_hook: Callable | None = None

    def start(self) -> None:
        """
        Runs the Avala client in production mode. This mode operates on a schedule, scanning registered directories for
        functions decorated with the `@exploit` decorator and scheduling attacks based on their configuration,
        including delay and batching settings. Exploits marked as `draft=True` in the decorator are ignored.

        Flags obtained from the executed exploits are submitted to the Avala server. The client keeps track of the
        successful attacks by storing hashes of used flag IDs to skip running the same attacks multiple times. This mode
        runs indefinitely until interrupted.
        """
        self._show_banner()
        self._validate_directories()

        self._scheduler = BlockingScheduler()
        self._client = APIClient.connect_or_exit(self._connection)

        logging.getLogger("apscheduler.executors.default").setLevel(logging.CRITICAL)

        self._scheduler.add_job(
            func=self._schedule_exploits,
            trigger="interval",
            seconds=self._client.schedule.tick_duration.total_seconds(),
            id="schedule_exploits",
            next_run_time=self._get_next_tick_start(),
        )

        if self._unsent_flag_storage is not None:
            self._scheduler.add_job(
                func=self._enqueue_pending_flags,
                trigger="interval",
                seconds=15,
                id="enqueue_pending_flags",
                next_run_time=datetime.now(),
            )

        try:
            self._scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print()  # Add a newline after the ^C
            self._scheduler.shutdown()
        finally:
            logger.info("🙌 Thanks for using Avala!")

    def watch(self) -> None:
        """
        Runs the Avala client in development mode. This mode monitors registered directories for file changes and scans
        modified files for functions decorated with the `@exploit` decorator. Detected exploits are executed immediately
        , ignoring delay and batching settings.

        Exploits marked with `reload=False` in the decorator are ignored. Flags obtained from the attacks are submitted
        to the Avala server. The client keeps track of the successful attacks by storing hashes of used flag IDs to skip
        running the same attacks multiple times. However, if an exploit is marked as `draft=True`, flag IDs are tracked
        but the attacks are not skipped, for easier testing and debugging during development.
        """
        event_handler = FileEventHandler(callback=self._launch_modified_exploits)
        observer = Observer()

        for directory in self._exploit_directories:
            observer.schedule(event_handler, directory.as_posix(), recursive=False, event_filter=[FileModifiedEvent])

        logger.info(
            "👀 Watching for changes in registered directories: <green>{directories}</>...",
            directories=", ".join([d.name for d in self._exploit_directories]),
        )
        observer.start()

        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            print()  # Add a newline after the ^C
            observer.stop()
        finally:
            observer.join()
            logger.info("🙌 Thanks for using Avala!")

    def register_directory(self, dir_path: str) -> None:
        """
        Registers a directory containing exploits. The directory path must be either absolute, or relative to your
        **current working directory when running the client**.

        :param dir_path: Path to the directory containing exploits.
        :type dir_path: str
        """
        path = Path(dir_path).resolve()
        if path not in self._exploit_directories:
            self._exploit_directories.add(path)

    def before_all(self):
        """
        Decorator for a function that will be executed before reloading and scheduling attacks, or at the beginning of
        each tick.

        This hook can be used to perform any setup or initialization before running attacks, such as pulling exploits
        from a git repository.
        """

        def decorator(func: Callable) -> Callable:
            self._before_all_hook = func
            return func

        # TODO: Not used yet.
        return decorator

    def after_all(self):
        """
        Decorator for a function that will be executed after all attacks are completed.

        This hook can be used to perform any cleanup or finalization after running attacks, such as cleaning up
        temporary files, sending a notification, etc.
        """

        def decorator(func) -> Callable:
            self._after_all_hook = func
            return func

        # TODO: Not used yet.
        return decorator

    def get_flag_ids(self) -> UnscopedFlagIds:
        """
        Fetches the current available flag ids fetched by the Avala server.

        :return: Unscoped flag ids covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedFlagIds
        """
        return self._client.fetch_flag_ids()

    def get_services(self) -> set[str]:
        """
        Fetches a set of names of the available services in flag ids.

        :return: Set of service names.
        :rtype: set[str]
        """
        return self._client.fetch_flag_ids().get_service_names()

    def submit_flags(
        self,
        flags: Iterable[str],
        host: str | None,
        service_name: str | None,
        exploit_alias: str | None,
    ) -> None:
        """
        Sends flags to the server for submission.

        :param flags: Flags to enqueue.
        :type flags: Iterable[str]
        :param host: Host of the target/victim team.
        :type host: str
        :param service_name: Name of the attacked service.
        :type service_name: str
        :param exploit_alias: Alias of the exploit that retrieved the flags.
        :type exploit_alias: str
        """
        self._client.enqueue(flags, host, self._worker_name, service_name, exploit_alias)

    def match_flags(self, output: Any) -> list[str]:
        """
        Matches flags in the attack's result using the flag format defined in the server settings.

        :param output: Any object that may contain flags when converted to a string. This should be the return value of
        an exploit function.
        :type output: Any
        :return: List of flags extracted from the output.
        :rtype: list[str]
        """
        return re.findall(self._client.game.flag_format, str(output))

    def _validate_directories(self) -> None:
        """
        Validates and filters out invalid (non-existent) registered exploit directories. Updates _exploit_directories
        in place.
        """
        valid_directories = set()
        for path in self._exploit_directories:
            if not path.exists() or not path.is_dir():
                logger.error("❌ Directory not found: {path}", path=path)
            else:
                valid_directories.add(path)

        logger.info(
            "📂 Registered exploit directories: <green>{directories}</>",
            directories=", ".join([d.name for d in valid_directories]),
        )

        self._exploit_directories = valid_directories

    def _fetch_or_load_flag_ids(self, long_poll: bool = False) -> UnscopedFlagIds | None:
        """
        Attempts to fetch flag IDs from the Avala server. If an error occurs while fetching, it tries to load cached
        flag IDs as a fallback. If the cached flag IDs are also not available, it returns None. All errors are logged.

        :param long_poll: If True, waits for the latest flag IDs from the server by long polling. If False, fetches the
        current available flag IDs from the server, defaults to False.
        :type long_poll: bool, optional
        :return: Unscoped flag ids covering flag IDs from all services, targets and ticks, or None if both fetching and
        loading from cache fails.
        :rtype: UnscopedFlagIds | None
        """
        try:
            return self._client.wait_for_flag_ids() if long_poll else self._client.fetch_flag_ids()
        except (HTTPStatusError, RequestError, ValidationError, Exception) as e:
            logger.error(
                "Failed to fetch flag IDs.\n\n<b>{error}</>\n{error_msg}\n",
                error=type(e).__name__,
                error_msg=e,
            )
            try:
                return self._client.get_cached_flag_ids()
            except (ValidationError, FileNotFoundError) as e:
                logger.error(
                    "Failed to load cached flag IDs.\n\n<b>{error}</>\n{error_msg}\n",
                    error=type(e).__name__,
                    error_msg=e,
                )
                return None

    def _reload_exploits(
        self,
        watched_file_path: Path | None = None,
    ) -> list[Exploit]:
        """
        Scans the registered directories for Python scripts containing exploits, executes them to compute
        configurations in `@exploit` decorators, and returns a list of exploits that need to be set up, scheduled,
        and run.

        :param watched_file_path: Path to the file that has been recently modified.
        :type watched_file_path: Path, optional
        :return: List of exploits to be set up, scheduled, and run afterwards.
        :rtype: list[Exploit]
        """

        should_execute: Callable[[Exploit], bool]

        exploits: list[Exploit] = []
        if watched_file_path is None:
            exploit_filepaths = (file for directory in self._exploit_directories for file in directory.glob("*.py"))
            should_execute = lambda e: not e.is_draft  # noqa: E731
        else:
            exploit_filepaths = [watched_file_path]
            should_execute = lambda e: e.is_reload_enabled  # noqa: E731

        for exploit_filepath in exploit_filepaths:
            try:
                spec = importlib.util.spec_from_file_location(exploit_filepath.stem, exploit_filepath.absolute())
                if spec is None:
                    raise Exception("Failed to load module spec.")

                module = importlib.util.module_from_spec(spec)
                patched_code = self._patch_pwntools(exploit_filepath)
                compiled_code = compile(patched_code, exploit_filepath.absolute(), "exec")
                exec(compiled_code, module.__dict__)
                for _, func in module.__dict__.items():
                    if (
                        callable(func)
                        and hasattr(func, "exploit")
                        and isinstance(func.exploit, Exploit)
                        and should_execute(func.exploit)
                    ):
                        exploits.append(func.exploit)
            except Exception as e:
                logger.error(
                    "Failed to load exploit from {file}: {error}",
                    file=exploit_filepath,
                    error=e,
                )

        logger.info(
            "📥 Loaded <b>{count}</> exploits: {exploits}.",
            count=len(exploits),
            exploits=", ".join(colorize(exploit.alias) for exploit in exploits),
        )
        return exploits

    def _launch_modified_exploits(self, watched_file_path: Path) -> None:
        """
        Scans for functions decorated with the `@exploit` decorator inside the given file that has been modified, checks
        if it's `reload` is not set to false, and runs the attacks immediately. The purpose of this mode is to run
        recently modified exploits independently of the tick schedule (i.e. running a new exploit as soon as possible
        without having to wait for the next tick) and to allow rapid exploit development. Flags obtained from the
        attacks are submitted to the Avala server. The client keeps track of used flag IDs to avoid running the
        same attacks multiple times, unless exploit's `draft` option is set to True.

        :param watched_file_path: Path to the file that has been recently modified.
        :type watched_file_path: Path
        """
        flag_ids = self._fetch_or_load_flag_ids()

        exploits = (e for e in self._reload_exploits(watched_file_path=watched_file_path))
        for exploit in exploits:
            if exploit.takes_flag_ids and flag_ids is None:
                logger.warning(
                    "⚠️  Skipping <b>{alias}</> as it requires flag IDs, but they are not available.",
                    alias=colorize(exploit.alias),
                )
                continue

            if not exploit.setup(
                game=self._client.game,
                flag_ids=flag_ids,
                blob_storage=self._blob_storage,
                flag_ids_hash_storage=self._flag_ids_hash_storage,
                batching=Batching(count=1),
            ):
                continue

            self._launch_exploit(exploit)

    def _schedule_exploits(self) -> None:
        """
        Handles reloading exploits, setting up, and scheduling them for execution. As a part of setting up exploits,
        it fetches flag IDs from the server by long polling, and passes them to the exploits that require them.

        Should be run as a scheduled job with the interval set to the tick duration.
        """
        executor = concurrent.futures.ThreadPoolExecutor()
        flag_ids_future = executor.submit(self._fetch_or_load_flag_ids, long_poll=True)

        now = datetime.now()

        # Sort exploits so that exploits that don't take flag IDs are scheduled first, followed by exploits that do.
        # This way, fetching flag ids (resolving flag_ids_future) won't block scheduling of exploits that don't need
        # flag ids.

        exploits = self._reload_exploits()
        ordered_exploits = [e for e in exploits if not e.takes_flag_ids] + [e for e in exploits if e.takes_flag_ids]

        for exploit in ordered_exploits:
            flag_ids = flag_ids_future.result() if exploit.takes_flag_ids else None
            if exploit.takes_flag_ids and flag_ids is None:
                logger.warning(
                    "⚠️  Skipping <b>{alias}</> as it requires flag IDs, but they are not available.",
                    alias=colorize(exploit.alias),
                )
                continue

            if not exploit.setup(
                game=self._client.game,
                flag_ids=flag_ids,
                blob_storage=self._blob_storage,
                flag_ids_hash_storage=self._flag_ids_hash_storage,
            ):
                continue
            for batch_idx in range(exploit.get_batch_count()):
                run_time = now + exploit.delay + exploit.get_batch_interval() * batch_idx
                self._scheduler.add_job(
                    func=self._launch_exploit,
                    args=(exploit, batch_idx),
                    trigger="date",
                    run_date=run_time,
                    misfire_grace_time=None,
                )
                logger.info(
                    "⏰ Exploit <b>{alias}</> (batch {batch_idx}/{total_batches}) will run at <b>{time}</>.",
                    alias=colorize(exploit.alias),
                    batch_idx=batch_idx + 1,
                    total_batches=exploit.get_batch_count(),
                    time=run_time.strftime("%H:%M:%S"),
                )

        executor.shutdown(wait=True)

    def _launch_exploit(self, exploit: Exploit, batch_idx: int = 0) -> None:
        """
        Launches the exploit in a separate process, collects flags from the attacks as soon as they complete and sends
        them to the Avala server for submission. Also handles timeouts and termination of the exploit process. Each
        exploit gets its own process, and each attack of the exploit gets its own thread.

        :param exploit: Exploit to launch.
        :type exploit: Exploit
        :param batch_idx: Index of the batch of hosts to attack, defaults to 0
        :type batch_idx: int, optional
        """
        logger.info(
            "🚀 Launching exploit <b>{alias}</> (batch {batch_idx}/{total_batches})...",
            alias=colorize(exploit.alias),
            batch_idx=batch_idx + 1,
            total_batches=exploit.get_batch_count(),
        )

        runner = Process(target=exploit.run_attacks, args=(batch_idx,))
        runner.start()

        while runner.is_alive():
            self._collect_and_enqueue(exploit)

        runner.join(exploit.timeout.total_seconds())
        if runner.is_alive():
            logger.info(
                "⌛ Terminating process for <b>{alias}</> (batch {batch_idx}/{total_batches}) due to timeout.",
                alias=colorize(exploit.alias),
                batch_idx=batch_idx + 1,
                total_batches=exploit.get_batch_count(),
            )
            runner.terminate()
            runner.join()
        else:
            logger.info(
                "✅ Finished running <b>{alias}</> (batch {batch_idx}/{total_batches}) in time.",
                alias=colorize(exploit.alias),
                batch_idx=batch_idx + 1,
                total_batches=exploit.get_batch_count(),
            )

        while self._collect_and_enqueue(exploit, drain=True):
            pass

    def _collect_and_enqueue(self, exploit: Exploit, drain: bool = False) -> bool:
        """
        Collects flags from the attacks as soon as they complete and sends them to the Avala server for submission.

        :param exploit: Exploit to collect flags from.
        :type exploit: Exploit
        :param drain: If True, collects all the remaining flags in a non-blocking way, used when all the attacks are
        done. Defaults to False.
        :type drain: bool, optional
        :return: True if there are more flags to collect, False otherwise.
        :rtype: bool
        """
        try:
            host, result = exploit.results.get(
                timeout=None if drain else 0.1,
                block=False if drain else True,
            )
        except Empty:
            return False

        flags = self.match_flags(result)
        if not flags:
            logger.warning(
                "⚠️  No flags retrieved from attacking <b>{host}</> via <b>{alias}</>.",
                host=colorize(host),
                alias=colorize(exploit.alias),
            )
            return True

        try:
            self._client.enqueue(flags, host, self._worker_name, exploit.service, exploit.alias)
        except Exception:
            logger.error(
                "🚨 Failed to submit flags from attacking <b>{host}</> via <b>{alias}</>. <d>{flags}</>",
                host=colorize(host),
                alias=colorize(exploit.alias),
                flags=truncate(", ".join(flags)),
            )
            if self._unsent_flag_storage:
                for flag in flags:
                    self._unsent_flag_storage.add(FlagsEnqueueBody(values=[flag], exploit=exploit.alias, host=host))
        finally:
            return True

    def _enqueue_pending_flags(self) -> None:
        """
        Job that periodically checks the connection with the server and tries to enqueue the pending flags collected
        during the server downtime.
        """
        if self._unsent_flag_storage.size():
            logger.warning(
                "🔄 <b>{count}</> flags are waiting to be submitted! Checking connection with the server...",
                count=self._unsent_flag_storage.size(),
            )
        else:
            logger.info("👌 No pending flags to submit.")
            return

        try:
            self._client.heartbeat()
        except Exception:
            logger.error(
                "🚨 Cannot establish connection with the server. <b>{count}</> flags are waiting to be submitted!",
                count=self._unsent_flag_storage.size(),
            )
            return
        else:
            logger.info(
                "🔌 Server is back online! Submitting pending <b>{count}</> flags...",
                count=self._unsent_flag_storage.size(),
            )

        flag = self._unsent_flag_storage.pop()
        while flag:
            try:
                self._client.enqueue(flag.values, flag.host, self._worker_name, flag.service, flag.exploit)
            except Exception:
                self._unsent_flag_storage.add(flag)
                logger.error(
                    "🚨 Cannot establish connection with the server. <b>{count}</> flags are waiting to be submitted!",
                    count=self._unsent_flag_storage.size(),
                )
                break
            else:
                flag = self._unsent_flag_storage.pop()

    def _get_next_tick_start(self) -> AwareDatetime:
        """
        Calculate the start time of the next tick.

        :return: Start time of the next tick.
        :rtype: AwareDatetime
        """
        first_tick_start = self._client.schedule.first_tick_start
        tick_duration = self._client.schedule.tick_duration
        now: AwareDatetime = datetime.now(tzlocal.get_localzone())

        game_has_started = first_tick_start > now

        if not game_has_started:
            return first_tick_start

        return now + tick_duration - (now - first_tick_start) % tick_duration

    @staticmethod
    def _patch_pwntools(file_path: Path) -> str:
        """
        Comments out `from pwn import *` to prevent "signal only works in main thread of the main interpreter" error

        :param code: Path to the Python file containing the exploit code.
        :type code: str
        :return: Exploit code without `from pwn import *`
        :rtype: str
        """
        return file_path.read_text().replace("from pwn import *\n", "# from pwn import *\n")

    def _show_banner(self) -> None:
        """
        Shows banner in the terminal. ✨
        """

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

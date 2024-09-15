import concurrent.futures
import importlib
import importlib.util
import re
from concurrent.futures import Future
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import func

from .api import APIClient
from .config import DOT_DIR_PATH, ConnectionConfig
from .database import create_tables, get_db, setup_db_conn
from .exploit import Exploit
from .models import PendingFlag, UnscopedAttackData
from .shared.logs import logger
from .shared.util import convert_to_local_tz, get_next_tick_start


class Avala:
    def __init__(
        self,
        protocol: str = "http",
        host: str = "localhost",
        port: int = 2024,
        username: str = "anon",
        password: str | None = None,
    ):
        """
        Initialize the Avala client. The client is used for scheduling and running attacks, extracting flags, and forwarding flags to the Avala server.

        :param protocol: Can be "http" or "https", defaults to "http".
        :type protocol: str, optional
        :param host: Host of the Avala server, defaults to "localhost"
        :type host: str, optional
        :param port: Port of the Avala server, defaults to 2024
        :type port: int, optional
        :param username: Player name, defaults to "anon"
        :type username: str, optional
        :param password: Password for the Avala server, defaults to None
        :type password: str | None, optional
        """
        self._config: ConnectionConfig = ConnectionConfig(
            protocol=protocol,
            host=host,
            port=port,
            username=username,
            password=password,
        )
        self._client: APIClient = None
        self._scheduler: BlockingScheduler = None

        self._exploit_directories: list[Path] = []
        self._before_all_hook = None
        self._after_all_hook = None

    def run(self):
        """
        Runs the Avala client in "production" mode. The client will start scheduling and running exploit functions decorated with `@exploit` in registered directories.
        Call this method after initializing the client and registering exploit directories.
        """
        self._show_banner()
        self._setup_db()
        self._check_directories()
        self._initialize_client()
        self._initialize_scheduler()
        self._client.get_attack_data()

        first_tick_start = convert_to_local_tz(
            self._client.schedule.first_tick_start,
            self._client.schedule.tz,
        )

        next_tick_start = get_next_tick_start(
            first_tick_start,
            timedelta(seconds=self._client.schedule.tick_duration),
        )

        # Schedule job that schedules exploits every tick.
        self._scheduler.add_job(
            func=self._schedule_exploits,
            trigger="interval",
            seconds=self._client.schedule.tick_duration,
            id="schedule_exploits",
            next_run_time=next_tick_start,
        )

        # Schedule job that enqueues pending (non forwarded) flags every 15 seconds.
        self._scheduler.add_job(
            func=self._enqueue_pending_flags,
            trigger="interval",
            seconds=15,
            id="enqueue_pending_flags",
        )

        try:
            self._scheduler.start()
        except KeyboardInterrupt:
            print()  # Add a newline after the ^C
            self._scheduler.shutdown()
            logger.info("Thanks for using Avala!")

    def workshop(self):
        """
        Runs draft exploits ("development" mode). This method runs exploit functions with `draft = True` in the registered directories, helping with the exploit development.
        This function can be called in a separate process while the client is already running in production mode. Call this method after initializing the client and registering exploit directories.
        """
        self._setup_db()
        self._check_directories()

        self._initialize_client(connect_then_import=False)

        try:
            attack_data = self._client.get_attack_data()
        except (RuntimeError, FileNotFoundError) as e:
            logger.error("{error} aa", error=e)
            exit(1)

        self._run_hook(self._before_all_hook)

        exploits = self._reload_exploits(attack_data)
        for exploit in exploits:
            exploit.setup() and exploit.run()

        self._run_hook(self._after_all_hook)

    def fire(self, selected_exploits: list[str]):
        """
        Runs selected exploits immediately, in given order. This function can be called in a separate process while the client is already running in production mode.
        Call this method after initializing the client and registering exploit directories.

        :param selected_exploits: Aliases of the exploits to run.
        :type selected_exploits: list[str]
        """
        self._setup_db()
        self._check_directories()

        self._initialize_client(connect_then_import=False)

        try:
            attack_data = self._client.get_attack_data()
        except (RuntimeError, FileNotFoundError) as e:
            logger.error("{error} aa", error=e)
            exit(1)

        self._run_hook(self._before_all_hook)

        exploits = [
            exploit
            for exploit in self._reload_exploits(attack_data, load_all=True)
            if exploit.alias in selected_exploits
        ]
        for exploit in exploits:
            exploit.setup() and exploit.run()

        self._run_hook(self._after_all_hook)

    def register_directory(self, dir_path: str):
        """
        Register a directory containing exploits. The directory path could be either absolute, or relative to your **current working directory when running the client**.

        :param dir_path: Path to the directory containing exploits.
        :type dir_path: str
        """
        path = Path(dir_path).resolve()
        if path not in self._exploit_directories:
            self._exploit_directories.append(path)

    def before_all(self):
        """
        Decorator for a function that will be executed before reloading and scheduling attacks, or at the beginning of each tick.

        This hook can be used to perform any setup or initialization before running attacks, such as pulling exploits from a git repository.
        """

        def decorator(func):
            self._before_all_hook = func
            return func

        return decorator

    def after_all(self):
        """
        Decorator for a function that will be executed after all attacks are completed.

        This hook can be used to perform any cleanup or finalization after running attacks, such as cleaning up temporary files, sending a notification, etc.
        """

        def decorator(func):
            self._after_all_hook = func
            return func

        return decorator

    def get_attack_data(self) -> UnscopedAttackData:
        """
        Fetches the current available attack data fetched by the Avala server.

        :return: Unscoped attack data covering flag IDs from all services, targets and ticks.
        :rtype: UnscopedAttackData
        """
        self._initialize_client(connect_then_import=False)
        return self._client.get_attack_data()

    def get_services(self) -> list[str]:
        """
        Fetches the list of services available in the attack data.

        :return: List of service names.
        :rtype: list[str]
        """
        return self.get_attack_data().get_services()

    def submit_flags(
        self,
        flags: list[str],
        exploit_alias: str = "manual",
        target: str = "unknown",
    ):
        """
        Sends flags to the server for enqueuing and duplicate filtering.

        :param flags: List of flags to enqueue.
        :type flags: list[str]
        :param exploit_alias: Alias of the exploit that retrieved the flags.
        :type exploit_alias: str
        :param target: IP address or hostname of the target/victim team.
        :type target: str
        """
        self._initialize_client(connect_then_import=False)

        enqueue_body = {
            "values": flags,
            "exploit": exploit_alias,
            "target": target,
        }

        response = requests.post(
            f"{self._client.conn_str}/flags/queue", json=enqueue_body
        )
        response.raise_for_status()

        return response.json()

    def match_flags(self, output: Any) -> list[str]:
        """
        Matches flags in the output using the flag format defined in the server settings.

        :param output: Any object that may contain flags when converted to a string.
        :type output: Any
        :return: List of flags extracted from the output.
        :rtype: list[str]
        """
        return re.findall(self._client.game.flag_format, str(output))

    def _initialize_client(self, connect_then_import: bool = True):
        """
        Initializes the API client. It imports settings from a JSON file as a fallback if the client fails to connect to the server.
        If the fallback fails too (FileNotFoundError), the client will exit.
        """
        self._client = APIClient(self._config)

        if connect_then_import:
            try:
                self._client.connect()
            except:
                self._client.import_settings()
            else:
                self._client.export_settings()
        elif (DOT_DIR_PATH / "api_client.json").exists():
            self._client.import_settings()
        else:
            try:
                self._client.connect()
            except:
                logger.error(
                    "Failed to connect to the server and configure the client."
                )
                exit(1)
            else:
                self._client.export_settings()

    def _initialize_scheduler(self):
        self._scheduler = BlockingScheduler()

    def _setup_db(self):
        setup_db_conn()
        create_tables()

    def _check_directories(self):
        """
        Validates and filters out invalid registered exploit directories.
        """
        valid_directories = []
        for path in self._exploit_directories:
            if not path.exists() or not path.is_dir():
                logger.error("Directory not found: {path}", path=path)
            else:
                valid_directories.append(path)

        logger.info(
            "Registered exploit directories: <green>{directories}</>",
            directories=", ".join([d.name for d in valid_directories]),
        )

        self._exploit_directories = valid_directories

    def _reload_exploits(
        self,
        attack_data: UnscopedAttackData | Future[UnscopedAttackData],
        load_all: bool = False,
    ) -> list[Exploit]:
        """
        Reloads exploits, collects their configuration and constructs a list of runnable `Exploit` objects.

        :param attack_data: Either an instance of `UnscopedAttackData` for development mode, or a future object that will return `UnscopedAttackData` for production mode.
        :type attack_data: UnscopedAttackData | Future[UnscopedAttackData]
        :param load_all: Whether to load all exploits, regardless of their draft status. Defaults to False.
        :type load_all: bool, optional
        :return: List of `Exploit` objects that can be setup and scheduled.
        :rtype: list[Exploit]
        """
        # Ready and available attack data indicates development mode.
        should_be_draft = isinstance(attack_data, UnscopedAttackData)

        def patch_pwntools(file_path: str) -> str:
            """
            Comments out `from pwn import *` to prevent "signal only works in main thread of the main interpreter" error.

            :param code: Path to the Python file containing the exploit code.
            :type code: str
            :return: Exploit code without `from pwn import *`
            :rtype: str
            """
            with open(python_file, "r") as file:
                return file.read().replace(
                    "from pwn import *\n", "# from pwn import *\n"
                )

        exploits: list[Exploit] = []
        for directory in self._exploit_directories:
            for python_file in directory.glob("*.py"):
                try:
                    python_module_name = python_file.stem
                    spec = importlib.util.spec_from_file_location(
                        python_module_name, python_file.absolute()
                    )
                    module = importlib.util.module_from_spec(spec)
                    patched_code = patch_pwntools(python_file)
                    compiled_code = compile(
                        patched_code, python_file.absolute(), "exec"
                    )
                    exec(compiled_code, module.__dict__)
                    for _, func in module.__dict__.items():
                        if (
                            callable(func)
                            and hasattr(func, "exploit_config")  # Has decorator
                            and (
                                load_all
                                or func.exploit_config.is_draft == should_be_draft
                            )
                        ):
                            e = Exploit(func.exploit_config, self._client, attack_data)
                            exploits.append(e)
                except Exception as e:
                    logger.error(
                        "Failed to load exploit from {file}: {error}",
                        file=python_file,
                        error=e,
                    )

        logger.debug("Loaded {count} exploits.", count=len(exploits))
        return exploits

    def _schedule_exploits(self):
        """
        Scheduled job that runs every tick to reload and schedule exploits. This job is also responsible for
        fetching attack_data and running before_all and after_all hooks.
        """
        executor = concurrent.futures.ThreadPoolExecutor()
        attack_data_future = executor.submit(self._client.wait_for_attack_data)

        if self._before_all_hook:
            self._before_all_hook()

        exploits = self._reload_exploits(attack_data_future)

        exploits_not_requiring_flag_ids, exploits_requiring_flag_ids = (
            [e for e in exploits if not e.requires_flag_ids],
            [e for e in exploits if e.requires_flag_ids],
        )

        now = datetime.now()

        # Exploits that do not require attack data are scheduled first because
        # they can be ran immediately, as opposed to the other exploits which
        # need to wait for the latest attack data.

        for exploit in exploits_not_requiring_flag_ids + exploits_requiring_flag_ids:
            if not exploit.setup():
                continue
            if not exploit.batches:
                self._scheduler.add_job(
                    exploit.run,
                    "date",
                    run_date=now + exploit.delay,
                    misfire_grace_time=None,
                )
            else:
                for batch_idx in range(len(exploit.batches)):
                    self._scheduler.add_job(
                        exploit.run,
                        "date",
                        run_date=now + exploit.delay + exploit.batching.gap * batch_idx,
                        args=[batch_idx],
                        misfire_grace_time=None,
                    )

        executor.shutdown(wait=True)

        if self._after_all_hook:
            self._after_all_hook()

    def _run_hook(self, func: Callable):
        """
        Runs a hook function, catches and logs any exceptions that occur.

        :param func: Hook function to run.
        :type func: Callable
        """
        if func:
            try:
                func()
            except Exception as e:
                logger.error(
                    "Error in {function}: {error}", function=func.__name__, error=e
                )

    def _enqueue_pending_flags(self):
        """
        Job that periodically checks the connection with the server and tries to push the pending flags
        collected during the server downtime.
        """
        with get_db() as db:
            try:
                self._client.heartbeat()
            except:
                logger.warning(
                    "⚠️ Cannot establish connection with the server. <b>{pending_flags}</> flags are waiting to be submitted.",
                    pending_flags=db.query(func.count(PendingFlag.value))
                    .filter(PendingFlag.submitted == False)
                    .scalar(),
                )
            else:
                results = (
                    db.query(
                        PendingFlag.target,
                        PendingFlag.alias,
                        func.group_concat(PendingFlag.value).label("flags"),
                    )
                    .filter(PendingFlag.submitted == False)
                    .group_by(PendingFlag.target, PendingFlag.alias)
                    .all()
                )

                if results:
                    logger.info("Server is back online! Submitting pending flags...")

                for row in results:
                    flags = row.flags.split(",")
                    self._client.enqueue(flags, row.alias, row.target)
                    db.query(PendingFlag).filter(
                        PendingFlag.target == row.target,
                        PendingFlag.alias == row.alias,
                    ).update({PendingFlag.submitted: True})

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

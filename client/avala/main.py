import importlib
import importlib.util
import concurrent.futures
from pathlib import Path
from sqlalchemy import func
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from concurrent.futures import Future
from .database import setup_db_conn, create_tables, get_db
from .models import UnscopedAttackData, PendingFlag
from .shared.logs import logger
from .shared.util import convert_to_local_tz, get_next_tick_start
from .config import ConnectionConfig
from .exploit import Exploit
from .api import APIClient


class Avala:
    def __init__(
        self,
        protocol: str = "http",
        host: str = "localhost",
        port: int = 2024,
        username: str = "anon",
        password: str | None = None,
    ):
        self.config: ConnectionConfig = ConnectionConfig(
            protocol=protocol,
            host=host,
            port=port,
            username=username,
            password=password,
        )
        self.client: APIClient = None
        self.scheduler: BlockingScheduler = None

        self.exploit_directories: list[Path] = []
        self.before_all_hook = None
        self.after_all_hook = None

    def run(self):
        self._show_banner()
        self._setup_db()
        self._check_directories()
        self._initialize_client()
        self._initialize_scheduler()
        self.client.get_attack_data()

        first_tick_start = convert_to_local_tz(
            self.client.schedule.first_tick_start,
            self.client.schedule.tz,
        )

        next_tick_start = get_next_tick_start(
            first_tick_start,
            timedelta(seconds=self.client.schedule.tick_duration),
        )

        self.scheduler.add_job(
            func=self._schedule_exploits,
            trigger="interval",
            seconds=self.client.schedule.tick_duration,
            id="schedule_exploits",
            next_run_time=next_tick_start,
        )

        self.scheduler.add_job(
            func=self._enqueue_pending_flags,
            trigger="interval",
            seconds=15,
            id="enqueue_pending_flags",
        )

        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            print()  # Add a newline after the ^C
            self.scheduler.shutdown()
            logger.info("Thanks for using Avala!")

    def workshop(self):
        self._setup_db()
        self._check_directories()

        self.client = APIClient(self.config)
        try:
            self.client.import_settings()
        except FileNotFoundError:
            self.client.connect()
            self.client.export_settings()

        attack_data = self.client.get_attack_data()

        self._run_hook(self.before_all_hook)

        exploits = self._reload_exploits(attack_data)
        for exploit in exploits:
            exploit.setup()
            exploit.run()

        self._run_hook(self.after_all_hook)

    def register_directory(self, dir_path: str):
        path = Path(dir_path).resolve()
        if path not in self.exploit_directories:
            self.exploit_directories.append(path)

    def before_all(self):
        def decorator(func):
            self.before_all_hook = func
            return func

        return decorator

    def after_all(self):
        def decorator(func):
            self.after_all_hook = func
            return func

        return decorator

    def _initialize_client(self):
        self.client = APIClient(self.config)
        try:
            self.client.connect()
        except:
            self.client.import_settings()
        else:
            self.client.export_settings()

    def _initialize_scheduler(self):
        self.scheduler = BlockingScheduler()

    def _setup_db(self):
        setup_db_conn()
        create_tables()

    def _check_directories(self):
        valid_directories = []
        for path in self.exploit_directories:
            if not path.exists() or not path.is_dir():
                logger.error(f"Directory not found: {path}")
            else:
                valid_directories.append(path)

        logger.info(
            f"Registered exploit directories: <green>{', '.join([d.name for d in valid_directories])}</>"
        )
        self.exploit_directories = valid_directories

    def _reload_exploits(
        self,
        attack_data: UnscopedAttackData | Future[UnscopedAttackData],
    ) -> list[Exploit]:
        should_be_draft = isinstance(attack_data, UnscopedAttackData)

        exploits: list[Exploit] = []
        for directory in self.exploit_directories:
            for python_file in directory.glob("*.py"):
                try:
                    python_module_name = python_file.stem
                    spec = importlib.util.spec_from_file_location(
                        python_module_name, python_file.absolute()
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    for _, func in module.__dict__.items():
                        if (
                            callable(func)
                            and hasattr(func, "exploit_config")
                            and func.exploit_config.is_draft == should_be_draft
                        ):
                            e = Exploit(func.exploit_config, attack_data)
                            exploits.append(e)
                except Exception as e:
                    logger.error(f"Failed to load exploit from {python_file}: {e}")

        logger.debug(f"Loaded {len(exploits)} exploits.")
        return exploits

    def _schedule_exploits(self):
        executor = concurrent.futures.ThreadPoolExecutor()
        attack_data_future = executor.submit(self.client.wait_for_attack_data)

        if self.before_all_hook:
            self.before_all_hook()

        exploits = self._reload_exploits(attack_data_future)

        automatic_target_exploits = [e for e in exploits if e.requires_flag_ids]
        manual_target_exploits = [e for e in exploits if not e.requires_flag_ids]

        now = datetime.now()

        # Manual target exploits are scheduled first because they can be ran immediately,
        # as opposed to automatic target exploits which need to wait for flag IDs.

        for exploit in manual_target_exploits + automatic_target_exploits:
            exploit.setup()
            if not exploit.batches:
                self.scheduler.add_job(
                    exploit.run,
                    "date",
                    run_date=now + exploit.delay,
                    misfire_grace_time=None,
                )
            else:
                for batch_idx in range(len(exploit.batches)):
                    self.scheduler.add_job(
                        exploit.run,
                        "date",
                        run_date=now + exploit.delay + exploit.batching.gap * batch_idx,
                        args=[batch_idx],
                        misfire_grace_time=None,
                    )

        executor.shutdown(wait=True)

        if self.after_all_hook:
            self.after_all_hook()

    def _run_hook(self, func):
        if func:
            try:
                func()
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")

    def _enqueue_pending_flags(self):
        with get_db() as db:
            try:
                self.client.heartbeat()
            except:
                logger.warning(
                    "⚠️ Cannot establish connection with the server. <bold>%d</> flags are waiting to be submitted."
                    % db.query(func.count(PendingFlag.value))
                    .filter(PendingFlag.submitted == False)
                    .scalar()
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
                    self.client.enqueue(flags, row.alias, row.target)
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

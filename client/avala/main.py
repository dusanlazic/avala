import importlib
import concurrent.futures
import importlib.util
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from concurrent.futures import Future
from .models import UnscopedAttackData
from .shared.logs import logger
from .shared.util import convert_to_local_tz
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

    def run(self):
        self._show_banner()
        self._check_directories()
        self._initialize_client()
        self._initialize_scheduler()

        next_tick_start = convert_to_local_tz(
            self.client.schedule.next_tick_start,
            self.client.schedule.tz,
        )

        self.scheduler.add_job(
            func=self._schedule_exploits,
            trigger="interval",
            seconds=self.client.schedule.tick_duration,
            id="schedule_exploits",
            next_run_time=next_tick_start,
        )

        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            print()  # Add a newline after the ^C
            self.scheduler.shutdown()
            logger.info("Thanks for using Avala!")

    def workshop(self):
        self._check_directories()

        self.client = APIClient(self.config)
        try:
            self.client.import_settings()
        except FileNotFoundError:
            self.client.connect()
            self.client.export_settings()

        attack_data = self.client.get_attack_data()

        exploits = self._reload_exploits(attack_data)
        for exploit in exploits:
            exploit.setup()
            exploit.run()

    def register_directory(self, dir_path):
        path = Path(dir_path)
        if path not in self.exploit_directories:
            self.exploit_directories.append(Path(dir_path))

    def _initialize_client(self):
        self.client = APIClient(self.config)
        self.client.connect()
        self.client.export_settings()

    def _initialize_scheduler(self):
        self.scheduler = BlockingScheduler()

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
                            and func.is_draft == should_be_draft
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

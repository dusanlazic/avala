import importlib
import concurrent.futures
import importlib.util
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
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

        self._show_banner()

    def run(self):
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

    def register_directory(self, dir_path):
        path = Path(dir_path)
        if not path.exists() or not path.is_dir():
            logger.error(f"Directory not found: {path}")
            return

        if path not in self.exploit_directories:
            self.exploit_directories.append(path)
            logger.info(f"Registered directory: {path}")

    def _initialize_client(self):
        self.client = APIClient(self.config)
        self.client.connect()
        self.client.export_settings()

    def _initialize_scheduler(self):
        self.scheduler = BlockingScheduler()

    def _reload_exploits(self, flag_ids_future):
        exploits = []
        for directory in self.exploit_directories:
            for python_file in directory.glob("*.py"):
                python_module_name = python_file.stem
                spec = importlib.util.spec_from_file_location(
                    python_module_name, python_file.absolute()
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for _, func in module.__dict__.items():
                    if callable(func) and hasattr(func, "exploit_config"):
                        exploits.append(Exploit(func.exploit_config, flag_ids_future))

        logger.debug(f"Loaded {len(exploits)} exploits.")
        return exploits

    def _schedule_exploits(self):
        executor = concurrent.futures.ThreadPoolExecutor()
        flag_ids_future = executor.submit(self.client.wait_for_flag_ids)

        exploits = self._reload_exploits(flag_ids_future)

        dynamic_target_exploits = [e for e in exploits if not e.targets]
        fixed_target_exploits = [e for e in exploits if e.targets]

        now = datetime.now()

        for exploit in fixed_target_exploits + dynamic_target_exploits:
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


if __name__ == "__main__":
    main()

import yaml
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from shared.logs import logger
from shared.util import convert_to_local_tz
from .config import load_user_config
from .exploit import Exploit
from .api import client


scheduler: BackgroundScheduler = BlockingScheduler()


def main():
    show_banner()
    load_user_config()

    client.connect()
    client.export_settings()

    next_tick_start = convert_to_local_tz(
        client.schedule.next_tick_start,
        client.schedule.tz,
    )

    scheduler.add_job(
        func=schedule_exploits,
        trigger="interval",
        seconds=client.schedule.tick_duration,
        id="schedule_exploits",
        next_run_time=next_tick_start,
    )

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print()  # Add a newline after the ^C
        scheduler.shutdown()
        logger.info("Thanks for using Avala!")


def reload_exploits():
    for ext in ["yml", "yaml"]:
        if Path(f"avala.{ext}").is_file():
            with open(f"avala.{ext}", "r") as file:
                user_config = yaml.safe_load(file)
                if not user_config:
                    logger.error(f"No configuration found in avala.{ext}. Exiting...")
                    return
                break
    else:
        logger.error("avala.yaml/.yml not found in the current working directory.")
        return

    exploits = [Exploit(e) for e in user_config.get("exploits")]

    logger.debug(f"Loaded {len(exploits)} exploits.")
    return exploits


def schedule_exploits():
    exploits = reload_exploits()
    for exploit in exploits:
        if not exploit.batching:
            scheduler.add_job(
                exploit.run, "date", run_date=datetime.now() + exploit.delay
            )
        elif exploit.batching:
            for batch_idx in range(len(exploit.batching.batches)):
                scheduler.add_job(
                    exploit.run,
                    "date",
                    run_date=datetime.now()
                    + exploit.delay
                    + exploit.batching.gap * batch_idx,
                    args=[batch_idx],
                )


def show_banner():
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

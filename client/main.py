import requests
from addict import Dict
from shared.logs import logger
from .config import config, load_user_config

game_info = None


def main():
    show_banner()
    load_user_config()

    connect_to_server()


def connect_to_server():
    global game_info

    if config.connect.password:
        conn_str = "%s://%s:%s@%s:%s" % (
            config.connect.protocol,
            config.connect.username,
            config.connect.password,
            config.connect.host,
            config.connect.port,
        )
    else:
        conn_str = "%s://%s:%s" % (
            config.connect.protocol,
            config.connect.host,
            config.connect.port,
        )

    logger.info(
        "Connecting to <blue>%s</blue>..."
        % conn_str.replace(":" + config.connect.password + "@", ":*****@")
    )

    try:
        requests.get(f"{conn_str}/connect/health").raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error("Failed to connect to the server: %s" % e)
        if e.response.status_code == 401:
            logger.error(
                "Note: Invalid credentials. Check the password with your teammates."
            )
        exit(1)

    logger.info("Fetching game information...")

    try:
        game_info = Dict(requests.get(f"{conn_str}/connect/game").json())
    except Exception as e:
        logger.error("Failed to fetch game information: %s" % e)
        exit(1)

    logger.info("Scheduling tasks...")


def show_banner():
    print(
        """\033[34;1m
      db                                            
     ;MM:                                           
    ,V^MM.    `7MM""Yq.  ,6"Yb.   `7M""MMF' ,6"Yb.  
   ,M  `MM      MM   j8 8)   MM     M  MM  8)   MM  
   AbmmmqMA     MM""Yq.  ,pm9MM    ,P  MM   ,pm9MM  
  A'     VML    MM   j8 8M   MM  . d'  MM  8M   MM  
.AMA.   .AMMA..JMMmmm9' `Moo9^Yo.8M' .JMML.`Moo9^Yo.
\033[0m"""
    )


if __name__ == "__main__":
    main()

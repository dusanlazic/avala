from shared.logs import logger
from .config import config, load_user_config
from .api import client


def main():
    show_banner()
    load_user_config()

    client.connect()
    logger.debug(client.params)


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

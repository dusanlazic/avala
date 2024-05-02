from shared.logs import logger
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from server.config import config

security = HTTPBasic()


def custom_security(request: Request):
    return security(request) if config["server"].get("password") else None


def authenticate(
    request: Request, credentials: HTTPBasicCredentials = Depends(custom_security)
):
    if config["server"].get("password") is None:
        return "Anon"

    if credentials.password != config["server"]["password"]:
        logger.error(
            "Invalid password attempt from <bold>%s</bold>." % request.client.host
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )
    return credentials.username

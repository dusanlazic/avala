from loguru import logger
from shared.logs import TextStyler as st
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from server.config import config

security = HTTPBasic()


def authenticate(
    request: Request, credentials: HTTPBasicCredentials = Depends(security)
):
    if config["server"].get("password") is None:
        return "Anon"

    if credentials.password != config["server"]["password"]:
        logger.error(f"Invalid password attempt from {st.bold(request.client.host)}.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )
    return credentials.username

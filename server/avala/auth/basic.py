from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from ..shared.logs import logger
from ..config import config

security = HTTPBasic()


async def custom_security(request: Request):
    if config.server.password:
        return await security(request)
    return None


async def authenticate(
    request: Request, credentials: HTTPBasicCredentials = Depends(custom_security)
):
    if config.server.password is None:
        return "Anon"

    if credentials.password != config.server.password:
        logger.error(
            "Invalid password attempt from <bold>%s</bold>." % request.client.host
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )
    return credentials.username

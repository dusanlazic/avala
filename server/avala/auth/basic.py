from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from ..shared.logs import logger
from ..config import config

httpbasic = HTTPBasic()


async def custom_security(request: Request):
    """
    Enforces HTTPBasic authentication if the password is configured.
    """
    if config.server.password:
        return await httpbasic(request)
    return None


async def authenticate(
    request: Request, credentials: HTTPBasicCredentials = Depends(custom_security)
) -> str:
    if config.server.password is None:
        return "Anon"

    if credentials.password != config.server.password:
        logger.error(
            "Invalid password attempt from <b>%s</>. Username: %s. User Agent: %s. Request path: %s."
            % (
                request.client.host,
                credentials.username,
                request.headers.get("User-Agent"),
                request.url.path,
            )
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )
    return credentials.username

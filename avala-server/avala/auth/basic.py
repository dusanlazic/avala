from avala_shared.logs import logger
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ..config import config

httpbasic = HTTPBasic()


async def get_current_user(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(httpbasic),
) -> str:
    """
    Enforces HTTP Basic Auth if a password is set in the config and returns the authenticated user's username.
    """
    if config.server.password is None:
        return "someone_at_%s" % request.client.host if request.client else "unknown"

    if credentials.password != config.server.password:
        logger.error(
            "Invalid password attempt from <b>{host}</>. Username: {username}. User Agent: {user_agent}. Request path: {path}.",
            host=request.client.host if request.client else "unknown",
            username=credentials.username,
            user_agent=request.headers.get("User-Agent"),
            path=request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )
    return credentials.username

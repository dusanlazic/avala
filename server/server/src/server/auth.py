from typing import Annotated

from avala.common.config import config
from avala.common.logger import logger
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

httpbasic = HTTPBasic(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(httpbasic),
) -> str:
    """
    Enforces HTTP Basic Auth if a password is set in the config and returns the authenticated user's username.
    """
    if config.server.password is None:
        return "someone_at_%s" % request.client.host if request.client else "unknown"

    if not credentials or credentials.password != config.server.password:
        logger.error(
            "Invalid password attempt from <b>{host}</>. Username: {username}. User Agent: {user_agent}. Request path: {path}.",  # noqa: E501
            host=request.client.host if request.client else "unknown",
            username=credentials.username if credentials else "none",
            user_agent=request.headers.get("User-Agent"),
            path=request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


CurrentUser = Annotated[str, Depends(get_current_user)]

import tzlocal
from shared.logs import logger
from typing import Annotated
from fastapi import APIRouter, Depends
from server.auth import basic_auth
from server.config import config

router = APIRouter(prefix="/connect", tags=["Connect"])


@router.get("/health")
async def health(_: Annotated[str, Depends(basic_auth)]):
    return {"status": "ok"}


@router.get("/params")
async def enqueue(_: Annotated[str, Depends(basic_auth)]):
    params = config.game.deepcopy()
    params.tz = tzlocal.get_localzone().key

    return params

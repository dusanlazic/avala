from shared.logs import logger
from typing import Annotated
from fastapi import APIRouter, Depends
from server.auth import basic_auth
from server.config import config

router = APIRouter(prefix="/connect", tags=["Connect"])


@router.get("/health")
async def health(_: Annotated[str, Depends(basic_auth)]):
    return {"status": "ok"}


@router.get("/game")
async def enqueue(_: Annotated[str, Depends(basic_auth)]):
    return config.game

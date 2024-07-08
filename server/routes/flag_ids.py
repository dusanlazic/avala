import json
from typing import Annotated
from fastapi import APIRouter, Depends
from server.auth import basic_auth
from server.state import get_state

router = APIRouter(prefix="/flag_ids", tags=["Flag IDs"])


@router.get("")
async def get_flag_ids():
    flag_ids = get_state("flag_ids")
    return (
        json.loads(flag_ids)
        if flag_ids
        else {
            "detail": "teams.json not fetched yet.",
        }
    )

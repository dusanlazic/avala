import json
from typing import Annotated
from fastapi import APIRouter, Depends
from server.auth import basic_auth
from server.state import state
from server.flag_ids import flag_ids_updated_event

router = APIRouter(prefix="/flag_ids", tags=["Flag IDs"])


@router.get("/subscribe")
async def get_latest_flag_ids(_: Annotated[str, Depends(basic_auth)]):
    await flag_ids_updated_event.wait()

    flag_ids = state.flag_ids
    return (
        json.loads(flag_ids)
        if flag_ids
        else {
            "detail": "teams.json not fetched yet.",
        }
    )


@router.get("/current")
async def get_current_flag_ids(_: Annotated[str, Depends(basic_auth)]):
    return (
        json.loads(state.flag_ids)
        if state.flag_ids
        else {
            "detail": "teams.json not fetched yet.",
        }
    )

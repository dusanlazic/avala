import json
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import basic_auth
from ..state import StateManager
from ..flag_ids import flag_ids_updated_event
from ..database import get_db

router = APIRouter(prefix="/flag_ids", tags=["Flag IDs"])


@router.get("/subscribe")
async def get_latest_flag_ids(
    _: Annotated[str, Depends(basic_auth)],
    db: Annotated[Session, Depends(get_db)],
):
    await flag_ids_updated_event.wait()

    with StateManager(db) as state:
        flag_ids = state.flag_ids
        return (
            json.loads(flag_ids)
            if flag_ids
            else {
                "detail": "teams.json not fetched yet.",
            }
        )


@router.get("/current")
async def get_current_flag_ids(
    _: Annotated[str, Depends(basic_auth)],
    db: Annotated[Session, Depends(get_db)],
):
    with StateManager(db) as state:
        flag_ids = state.flag_ids
        return (
            json.loads(flag_ids)
            if flag_ids
            else {
                "detail": "teams.json not fetched yet.",
            }
        )

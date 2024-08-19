import json
from typing import Annotated
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from ..auth import basic_auth
from ..state import StateManager
from ..attack_data import attack_data_updated_event
from ..database import get_db_for_request

router = APIRouter(prefix="/attack_data", tags=["Attack data"])


@router.get("/subscribe")
async def get_latest_attack_data(
    _: Annotated[str, Depends(basic_auth)],
    db: Annotated[Session, Depends(get_db_for_request)],
    response: Response,
):
    """
    Waits for and returns the latest attack data when it is updated.
    """
    await attack_data_updated_event.wait()

    with StateManager(db) as state:
        attack_data = state.attack_data

    if attack_data:
        return json.loads(attack_data)
    else:
        response.status_code = status.HTTP_202_ACCEPTED
        return {
            "detail": "Attack data not fetched yet.",
        }


@router.get("/current")
async def get_current_attack_data(
    _: Annotated[str, Depends(basic_auth)],
    db: Annotated[Session, Depends(get_db_for_request)],
    response: Response,
):
    """
    Returns the current available attack data.
    """
    with StateManager(db) as state:
        attack_data = state.attack_data

    if attack_data:
        return json.loads(attack_data)
    else:
        response.status_code = status.HTTP_202_ACCEPTED
        return {
            "detail": "Attack data not fetched yet.",
        }

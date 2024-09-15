import json
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ..attack_data import attack_data_updated_event
from ..auth import CurrentUser
from ..database import get_db
from ..state import StateManager

router = APIRouter(prefix="/attack-data", tags=["Attack data"])


@router.get("/subscribe")
async def get_latest_attack_data(
    username: CurrentUser,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
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
def get_current_attack_data(
    username: CurrentUser,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
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

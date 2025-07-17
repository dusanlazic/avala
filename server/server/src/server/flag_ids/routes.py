from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status

from server.auth import get_current_user
from server.database import Database

from . import service

router = APIRouter(prefix="/flag-ids", tags=["flag_ids"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[Any])
async def get_flag_ids(
    db: Database,
    response: Response,
    wait: bool = Query(False, description="Long poll for the newest flag IDs."),
):
    """
    Returns the current flag IDs. If `wait=true`, waits for updates before returning.
    """
    if wait:
        await service.flag_ids_updated_event.wait()

    flag_ids = await service.get_flag_ids(db)

    if not flag_ids:
        response.status_code = status.HTTP_202_ACCEPTED
        return {"detail": "Flag IDs not fetched yet."}
    return flag_ids

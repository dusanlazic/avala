from fastapi import APIRouter, Response, status

from database import Database

from . import service

router = APIRouter(prefix="/flag-ids", tags=["flag_ids"])


@router.get("/subscribe")
async def wait_for_flag_id(db: Database, response: Response):
    """
    Waits for and returns the latest flag IDs when they are updated.
    """
    await service.flag_ids_updated_event.wait()

    flag_ids = await service.get_flag_ids(db)

    if not flag_ids:
        response.status_code = status.HTTP_202_ACCEPTED
        return {"detail": "Flag IDs not fetched yet."}
    return flag_ids


@router.get("/current")
async def get_current_flag_ids(db: Database, response: Response):
    """
    Returns the current flag IDs.
    """
    flag_ids = await service.get_flag_ids(db)

    if not flag_ids:
        response.status_code = status.HTTP_202_ACCEPTED
        return {"detail": "Flag IDs not fetched yet."}
    return flag_ids

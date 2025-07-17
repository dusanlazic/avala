from fastapi import APIRouter, Depends, HTTPException, Request

from server.auth import get_current_user
from server.database import Database

from . import service
from .schemas import WorkerRegistrationRequest, WorkerResponse

router = APIRouter(prefix="/workers", tags=["workers", "experimental"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[WorkerResponse])
async def get_all(db: Database):
    """
    Get all registered workers.
    """
    return await service.get_all(db)


@router.get("/{alias}", response_model=WorkerResponse)
async def get_by_alias(alias: str, db: Database):
    """
    Get a worker by alias.
    """
    worker = await service.get_by_alias(alias, db)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found.")
    return worker


@router.post("", response_model=WorkerResponse)
async def register_or_update(worker: WorkerRegistrationRequest, db: Database, request: Request):
    """
    Register a new worker or update an existing one.
    """
    ip = service.get_real_ip(request)
    if not ip:
        raise HTTPException(status_code=400, detail="Failed to read worker IP address. Check your proxy settings.")
    return await service.register_or_update(ip, worker.alias, worker.dev_mode, worker.registered_exploits, db)

from datetime import datetime, timezone
from typing import Sequence

from avala.common.config import config
from avala.common.logger import logger
from fastapi import Request
from sqlalchemy import select

from database import Database

from .models import Worker


def get_real_ip(request: Request) -> str | None:
    if config.server.proxy_header:
        return request.headers.get(config.server.proxy_header, None)
    else:
        return request.client.host if request.client else None


async def get_all(db: Database) -> Sequence[Worker]:
    stmt = select(Worker).order_by(Worker.created_at)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_by_alias(alias: str, db: Database) -> Worker | None:
    stmt = select(Worker).where(Worker.alias == alias)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def register_or_update(
    ip: str,
    alias: str,
    dev_mode: bool,
    registered_exploits: list[str],
    db: Database,
) -> Worker:
    existing_worker = (await db.execute(select(Worker).where(Worker.alias == alias))).scalar_one_or_none()
    if existing_worker:
        existing_worker.dev_mode = dev_mode
        existing_worker.ip = ip
        existing_worker.registered_exploits = ",".join(registered_exploits)
        existing_worker.last_seen = datetime.now(timezone.utc)

        db.add(existing_worker)
        await db.commit()
        await db.refresh(existing_worker)
        logger.debug(existing_worker.updated_at)
        return existing_worker

    new_worker = Worker(
        alias=alias,
        dev_mode=dev_mode,
        ip=ip,
        registered_exploits=",".join(registered_exploits),
    )
    db.add(new_worker)
    await db.commit()
    await db.refresh(new_worker)
    return new_worker

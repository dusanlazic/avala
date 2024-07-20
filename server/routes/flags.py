import time
from fastapi import APIRouter, Depends, BackgroundTasks, Query, HTTPException
from pyparsing import ParseException
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from server.auth import basic_auth
from server.models import Flag
from server.database import get_db
from server.mq.rabbit_async import rabbit
from server.scheduler import get_tick_number
from server.config import config
from server.broadcast import broadcast
from server.search import parse_query, build_query
from shared.logs import logger
from shared.util import colorize
from typing import Annotated, List, Optional

router = APIRouter(prefix="/flags", tags=["Flags"])


class EnqueueBody(BaseModel):
    values: list[str]
    exploit: str
    target: str


@router.post("/queue")
async def enqueue(
    flags: EnqueueBody,
    bg: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    username: Annotated[str, Depends(basic_auth)],
):
    current_tick = get_tick_number()
    existing_flags = db.query(Flag.value).filter(Flag.value.in_(flags.values)).all()
    dup_flag_values = {flag.value for flag in existing_flags}
    new_flag_values = list(set(flags.values) - dup_flag_values)

    new_flags = [
        Flag(
            value=value,
            exploit=flags.exploit,
            target=flags.target,
            tick=current_tick,
            player=username,
            status="queued",
        )
        for value in new_flag_values
    ]
    db.bulk_save_objects(new_flags)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()

    for flag in new_flag_values:
        bg.add_task(rabbit.queues.submission_queue.put, flag, ttl=config.game.flag_ttl)

    await broadcast.publish(
        channel="incoming_flags",
        message={
            "target": flags.target,
            "exploit": flags.exploit,
            "player": username,
            "duplicates": len(dup_flag_values),
            "enqueued": len(new_flag_values),
        },
    )

    logger.info(
        "📥 <bold>%d</> flags from <bold>%s</> via <bold>%s</> by <bold>%s</> (<green>%d</> new, <yellow>%d</> duplicates)."
        % (
            len(flags.values),
            colorize(flags.target),
            colorize(flags.exploit),
            username,
            len(new_flag_values),
            len(dup_flag_values),
        )
    )

    return {
        "discarded": len(dup_flag_values),
        "enqueued": len(new_flag_values),
    }


@router.get("/db-stats")
async def db_stats(db: Annotated[Session, Depends(get_db)]):
    current_tick = get_tick_number()

    current_tick_flags = db.query(Flag).filter(Flag.tick == current_tick).count()
    last_tick_flags = db.query(Flag).filter(Flag.tick == current_tick - 1).count()

    manually_submitted = (
        db.query(Flag)
        .filter(Flag.target == "unknown", Flag.exploit == "manual")
        .count()
    )

    return {
        "current_tick": current_tick_flags,
        "last_tick": last_tick_flags,
        "manual": manually_submitted,
    }


@router.get("/search")
async def search(
    query: Optional[str] = Query(None),
    page: int = Query(1),
    show: int = Query(25, le=100),
    sort: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    username: Annotated[str, Depends(basic_auth)] = None,
):
    if not query:
        raise HTTPException(status_code=400, detail="Missing query.")

    # Build search query
    try:
        parsed_query = parse_query(query)
        sqlalchemy_query = build_query(parsed_query)
    except ParseException:
        raise HTTPException(status_code=400, detail="Invalid query.")
    except AttributeError as e:
        raise HTTPException(
            status_code=400, detail=f"Unknown field {e.args[0].split()[-1]}."
        )
    except Exception as e:
        logger.debug(e.with_traceback())
        raise HTTPException(
            status_code=500,
            detail="Something broke while your query was being processed: %s" % e,
        )

    # Select sorting
    sort_expressions = (
        [
            (
                getattr(Flag, item["field"]).desc()
                if item["direction"] == "desc"
                else getattr(Flag, item["field"])
            )
            for item in sort
        ]
        if sort
        else []
    )

    # Run query
    start = time.time()
    try:
        query = db.query(Flag).filter(sqlalchemy_query).order_by(*sort_expressions)
        results = [
            {
                "tick": flag.tick,
                "timestamp": flag.timestamp,
                "player": flag.player,
                "exploit": flag.exploit,
                "target": flag.target,
                "status": flag.status,
                "value": flag.value,
                "response": flag.response,
            }
            for flag in query.offset((page - 1) * show).limit(show).all()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to run the query: %s" % e)
    elapsed = time.time() - start

    total = db.query(func.count(Flag.id)).filter(sqlalchemy_query).scalar()
    total_pages = (total + show - 1) // show

    metadata = {
        "paging": {
            "current": page,
            "last": total_pages,
            "hasNext": page + 1 <= total_pages,
            "hasPrev": page > 1,
        },
        "results": {"total": total, "fetched": len(results), "executionTime": elapsed},
    }

    return {"results": results, "metadata": metadata}

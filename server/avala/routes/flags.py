import time
from fastapi import APIRouter, Depends, BackgroundTasks, Query, HTTPException
from pyparsing import ParseException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Annotated, List, Optional
from ..auth import CurrentUser
from ..models import Flag
from ..schemas import (
    FlagEnqueueRequest,
    FlagEnqueueResponse,
    SearchResults,
    SearchResult,
    SearchMetadata,
    SearchPagingMetadata,
    SearchStatsMetadata,
    SearchQueryParams,
)
from ..database import get_db
from ..mq.rabbit_async import rabbit
from ..scheduler import get_tick_number
from ..config import AvalaConfig
from ..search import parse_query, build_query
from ..shared.logs import logger
from ..shared.util import colorize

router = APIRouter(prefix="/flags", tags=["Flags"])


@router.post("/queue", response_model=FlagEnqueueResponse)
def enqueue(
    flags: FlagEnqueueRequest,
    bg: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    username: CurrentUser,
    config: AvalaConfig,
) -> FlagEnqueueResponse:
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

    for flag in new_flag_values:
        bg.add_task(
            rabbit.get_queue("submission_queue").put,
            flag,
            ttl=str(config.game.flag_ttl * 1000),
        )

    # await broadcast.publish(
    #     channel="incoming_flags",
    #     message={
    #         "target": flags.target,
    #         "exploit": flags.exploit,
    #         "player": username,
    #         "duplicates": len(dup_flag_values),
    #         "enqueued": len(new_flag_values),
    #     },
    # )

    logger.info(
        "{status} <b>{total_flags}</> flags from <b>{target}</> via <b>{exploit}</> by <b>{user}</> (<green>{new_flags}</> new, <yellow>{dup_flags}</> duplicates).",
        status="✅" if len(new_flag_values) else "❗",
        total_flags=len(flags.values),
        target=colorize(flags.target),
        exploit=colorize(flags.exploit),
        user=username,
        new_flags=len(new_flag_values),
        dup_flags=len(dup_flag_values),
    )

    return FlagEnqueueResponse(
        enqueued=len(new_flag_values),
        discarded=len(dup_flag_values),
    )


@router.get("/search", response_model=SearchResults)
def search(
    username: CurrentUser,
    query: str | None = Query(None),
    page: int = Query(1, ge=1),
    show: int = Query(25, le=100),
    sort: List[str] | None = Query(None),
    db: Session = Depends(get_db),
) -> SearchResults:
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
        logger.debug(e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Something broke while your query was being processed: %s" % e,
        )

    # Select sorting
    sort_expressions = []
    if sort:
        for item in sort:
            field, *order = item.split()
            expression = getattr(Flag, field)
            if order and order[0] == "desc":
                expression = expression.desc()
            sort_expressions.append(expression)

    # Run query
    start = time.time()
    try:
        query = db.query(Flag).filter(sqlalchemy_query).order_by(*sort_expressions)
        results = [
            SearchResult.model_validate(flag)
            for flag in query.offset((page - 1) * show).limit(show).all()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to run the query: %s" % e)
    elapsed = time.time() - start

    total = db.query(func.count(Flag.id)).filter(sqlalchemy_query).scalar()
    total_pages = (total + show - 1) // show

    return SearchResults(
        results=results,
        metadata=SearchMetadata(
            results=SearchStatsMetadata(
                total=total, fetched=len(results), execution_time=elapsed
            ),
            paging=SearchPagingMetadata(
                current=page,
                last=total_pages,
                has_next=page + 1 <= total_pages,
                has_prev=page > 1,
            ),
        ),
    )

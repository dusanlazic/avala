from fastapi import APIRouter

from server.database import Database
from server.messaging import Channel

from . import service
from .schemas import TotalNumbersResponse

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/hosts", response_model=list[str])
async def get_target_hosts(db: Database):
    """
    Retrieve the list of target hosts.
    """
    hosts = await service.get_target_hosts(db)
    return sorted(hosts)


@router.get("/services", response_model=list[str])
async def get_target_services(db: Database):
    """
    Retrieve the list of target services.
    """
    services = await service.get_target_services(db)
    return sorted(services)


@router.get("/exploits", response_model=list[str])
async def get_distinct_exploits(db: Database):
    """
    Retrieve the list of distinct exploits.
    """
    exploits = await service.get_distinct_exploits(db)
    return sorted(exploits)


@router.get("/totals", response_model=TotalNumbersResponse)
async def get_total_numbers(db: Database):
    """
    Retrieve the total number of flags in queue, accepted and rejected flags.
    """
    return TotalNumbersResponse(
        queued=await service.count_flags_by_status_and_tick_range(db, "queued"),
        accepted=await service.count_flags_by_status_and_tick_range(db, "accepted"),
        rejected=await service.count_flags_by_status_and_tick_range(db, "rejected"),
    )


@router.get("/current-tick", response_model=TotalNumbersResponse)
async def get_current_tick_numbers(db: Database):
    """
    Retrieve the number of flags queued, accepted and rejected during the current tick.
    """
    current_tick = service.get_tick_number()

    return TotalNumbersResponse(
        queued=await service.count_flags_by_status_and_tick_range(
            db, "queued", before_tick=current_tick, after_tick=current_tick
        ),
        accepted=await service.count_flags_by_status_and_tick_range(
            db, "accepted", before_tick=current_tick, after_tick=current_tick
        ),
        rejected=await service.count_flags_by_status_and_tick_range(
            db, "rejected", before_tick=current_tick, after_tick=current_tick
        ),
    )


@router.get("/tick-graph", response_model=list[int])
async def get_tick_graph(db: Database, status: str | None = None, exploit: str | None = None):
    """
    Retrieve the tick graph for flags with the given status and exploit.
    """
    return await service.compute_tick_graph(db, status=status, exploit=exploit)


@router.get("/attack-heatmap", response_model=list[list[int]])
async def get_attack_heatmap(
    db: Database,
    status: str | None = None,
    exploit: str | None = None,
    last_n_ticks: int | None = None,
):
    """
    Retrieve the attack heatmap for flags with the given status and exploit.
    """
    return await service.compute_attack_heatmap(db, status=status, exploit=exploit, last_n_ticks=last_n_ticks)


@router.get("/exploits-table")
async def get_exploits_table(
    db: Database,
):
    """
    Retrieve the contents for filling the exploits table.
    """
    return await service.fetch_exploit_data(db)

from datetime import datetime

from fastapi import APIRouter, Query, status

from app.schemas import (
    EventIn,
    ShardEventOut,
    ShardEventsPage,
    ShardMatchEventsPage,
    ShardRouteOut,
    ShardsOut,
    TopScorerOut,
)
from app.services import shards as service

router = APIRouter(prefix="/api/shards", tags=["shards"])


@router.get(
    "",
    response_model=ShardsOut,
    summary="COUNT(*) на каждом шарде и сумма; упавший шард помечается ok=false",
)
def list_shards():
    return service.list_shards()


@router.get(
    "/route",
    response_model=ShardRouteOut,
    summary="Router: на каком шарде лежат события матча",
)
def route(match_id: int = Query(..., description="shard key")):
    return service.route(match_id)


@router.get(
    "/matches/{match_id}/events",
    response_model=ShardMatchEventsPage,
    summary="События матча: один шард + JOIN с игроками и матчем в коде backend",
)
def list_match_events(
    match_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return service.list_match_events(match_id, page, page_size)


@router.get(
    "/events",
    response_model=ShardEventsPage,
    summary="Лента событий, ORDER BY created_at DESC: с match_id один шард, без него все шарды + merge",
)
def list_events(
    event_type: str | None = Query(None, description="GOAL | ASSIST | YELLOW_CARD | RED_CARD | SUBSTITUTION"),
    match_id: int | None = Query(None, description="shard key"),
    player_id: int | None = None,
    date_from: datetime | None = Query(None, alias="from", description="created_at >="),
    date_to: datetime | None = Query(None, alias="to", description="created_at <="),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return service.list_events(event_type, match_id, player_id, date_from, date_to, page, page_size)


@router.get(
    "/reports/top-scorers",
    response_model=list[TopScorerOut],
    summary="Агрегация по всем шардам: частичные суммы по игрокам, сложение и сортировка в backend",
)
def top_scorers(
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    limit: int = Query(10, ge=1, le=100),
):
    return service.top_scorers(date_from, date_to, limit)


@router.get(
    "/events/{event_id}",
    response_model=ShardEventOut,
    summary="Событие по id: без shard key спрашиваем все шарды",
)
def get_event(event_id: int):
    return service.get_event(event_id)


@router.post(
    "/events",
    response_model=ShardEventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать событие: router выбирает шард по match_id",
)
def create_event(payload: EventIn):
    return service.create_event(payload)

from datetime import datetime

from fastapi import APIRouter, Query, status

from app.schemas import EventDetailOut, MatchIn, MatchOut, Page
from app.services import events as events_service
from app.services import matches as service

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.get(
    "",
    response_model=Page[MatchOut],
    summary="Список матчей: JOIN с турниром и обеими командами + фильтры и пагинация",
)
def list_matches(
    status_filter: str | None = Query(None, alias="status", description="SCHEDULED | FINISHED | CANCELLED"),
    tournament_id: int | None = None,
    team_id: int | None = Query(None, description="матчи команды дома или в гостях"),
    date_from: datetime | None = Query(None, alias="from", description="started_at >="),
    date_to: datetime | None = Query(None, alias="to", description="started_at <="),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None, description="started_at | created_at | status | tournament | id, с '-' для DESC"),
):
    return service.list_matches(
        status_filter, tournament_id, team_id, date_from, date_to, page, page_size, sort
    )


@router.get("/{match_id}", response_model=MatchOut, summary="Матч по id")
def get_match(match_id: int):
    return service.get_match(match_id)


@router.get(
    "/{match_id}/events",
    response_model=Page[EventDetailOut],
    summary="События матча (связанная сущность)",
)
def list_match_events(
    match_id: int,
    event_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None, description="по умолчанию по минуте матча"),
):
    return events_service.list_events_by_match(match_id, event_type, page, page_size, sort)


@router.post("", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
def create_match(payload: MatchIn):
    return service.create_match(payload)


@router.put("/{match_id}", response_model=MatchOut)
def update_match(match_id: int, payload: MatchIn):
    return service.update_match(match_id, payload)


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: int):
    service.delete_match(match_id)

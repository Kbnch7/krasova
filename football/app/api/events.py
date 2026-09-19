from datetime import datetime

from fastapi import APIRouter, Query, status

from app.schemas import EventDetailOut, EventIn, EventOut, EventUpdate, Page
from app.services import events as service

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get(
    "",
    response_model=Page[EventDetailOut],
    summary="События матчей: JOIN с матчами, игроками и командами + фильтры и пагинация",
)
def list_events(
    event_type: str | None = Query(None, description="GOAL | ASSIST | YELLOW_CARD | RED_CARD | SUBSTITUTION"),
    match_id: int | None = None,
    player_id: int | None = None,
    team_id: int | None = Query(None, description="команда игрока"),
    tournament_id: int | None = None,
    date_from: datetime | None = Query(None, alias="from", description="created_at >="),
    date_to: datetime | None = Query(None, alias="to", description="created_at <="),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None, description="created_at | minute | event_type | id, с '-' для DESC"),
):
    return service.list_events(
        event_type, match_id, player_id, team_id, tournament_id,
        date_from, date_to, page, page_size, sort,
    )


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int):
    return service.get_event(event_id)


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventIn):
    return service.create_event(payload)


@router.put("/{event_id}", response_model=EventOut)
def update_event(event_id: int, payload: EventUpdate):
    return service.update_event(event_id, payload)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int):
    service.delete_event(event_id)

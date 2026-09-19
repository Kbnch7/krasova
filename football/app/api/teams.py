from fastapi import APIRouter, Query, status

from app.schemas import EventDetailOut, MatchOut, Page, PlayerOut, TeamIn, TeamOut
from app.services import events as events_service
from app.services import matches as matches_service
from app.services import players as players_service
from app.services import teams as service

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=Page[TeamOut], summary="Список команд")
def list_teams(
    search: str | None = Query(None, description="поиск по названию (ILIKE)"),
    city: str | None = None,
    tournament: str | None = Query(None, description="название турнира (связь many-to-many)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None, description="id | name | city | founded_year | created_at, с '-' для DESC"),
):
    return service.list_teams(search, city, tournament, page, page_size, sort)


@router.get("/{team_id}", response_model=TeamOut, summary="Команда по id")
def get_team(team_id: int):
    return service.get_team(team_id)


@router.get("/{team_id}/players", response_model=Page[PlayerOut], summary="Игроки команды")
def list_team_players(
    team_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = None,
):
    return players_service.list_players_by_team(team_id, page, page_size, sort)


@router.get("/{team_id}/matches", response_model=Page[MatchOut], summary="Матчи команды")
def list_team_matches(
    team_id: int,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = None,
):
    return matches_service.list_matches_by_team(team_id, status_filter, page, page_size, sort)


@router.get("/{team_id}/events", response_model=Page[EventDetailOut], summary="События команды")
def list_team_events(
    team_id: int,
    event_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = None,
):
    return events_service.list_events_by_team(team_id, event_type, page, page_size, sort)


@router.post("", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(payload: TeamIn):
    return service.create_team(payload)


@router.put("/{team_id}", response_model=TeamOut)
def update_team(team_id: int, payload: TeamIn):
    return service.update_team(team_id, payload)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(team_id: int):
    service.delete_team(team_id)

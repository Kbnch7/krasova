from fastapi import APIRouter, Query, status

from app.schemas import EventDetailOut, Page, PlayerIn, PlayerOut
from app.services import events as events_service
from app.services import players as service

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("", response_model=Page[PlayerOut], summary="Список игроков: поиск, фильтры, пагинация")
def list_players(
    search: str | None = Query(None, description="поиск по имени игрока или названию команды (ILIKE)"),
    team_id: int | None = None,
    position: str | None = Query(None, description="GK | DEF | MID | FWD"),
    tournament: str | None = Query(None, description="название турнира (связь many-to-many)"),
    year_from: int | None = Query(None, description="год рождения >="),
    year_to: int | None = Query(None, description="год рождения <="),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None, description="id | full_name | birth_year | shirt_number | created_at | team, с '-' для DESC"),
):
    return service.list_players(
        search, team_id, position, tournament, year_from, year_to, page, page_size, sort
    )


@router.get("/{player_id}", response_model=PlayerOut, summary="Игрок по id")
def get_player(player_id: int):
    return service.get_player(player_id)


@router.get(
    "/{player_id}/events",
    response_model=Page[EventDetailOut],
    summary="События игрока (связанная сущность)",
)
def list_player_events(
    player_id: int,
    event_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = None,
):
    return events_service.list_events_by_player(player_id, event_type, page, page_size, sort)


@router.post("", response_model=PlayerOut, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerIn):
    return service.create_player(payload)


@router.put("/{player_id}", response_model=PlayerOut)
def update_player(player_id: int, payload: PlayerIn):
    return service.update_player(player_id, payload)


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player(player_id: int):
    service.delete_player(player_id)

from fastapi import APIRouter, status

from app.schemas import TournamentIn, TournamentOut
from app.services import tournaments as service

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])


@router.get("", response_model=list[TournamentOut], summary="Список турниров")
def list_tournaments():
    return service.list_tournaments()


@router.get("/{tournament_id}", response_model=TournamentOut)
def get_tournament(tournament_id: int):
    return service.get_tournament(tournament_id)


@router.post("", response_model=TournamentOut, status_code=status.HTTP_201_CREATED)
def create_tournament(payload: TournamentIn):
    return service.create_tournament(payload)


@router.put("/{tournament_id}", response_model=TournamentOut)
def update_tournament(tournament_id: int, payload: TournamentIn):
    return service.update_tournament(tournament_id, payload)


@router.delete("/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tournament(tournament_id: int):
    service.delete_tournament(tournament_id)

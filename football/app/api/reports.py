from datetime import datetime

from fastapi import APIRouter, Query

from app.schemas import TeamStatOut, TopScorerOut, TournamentStatOut
from app.services import reports as service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get(
    "/top-scorers",
    response_model=list[TopScorerOut],
    summary="Агрегация: бомбардиры за период",
)
def top_scorers(
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    tournament_id: int | None = None,
    limit: int = Query(10, ge=1, le=100),
):
    return service.top_scorers(date_from, date_to, tournament_id, limit)


@router.get(
    "/tournaments",
    response_model=list[TournamentStatOut],
    summary="Агрегация: матчи и голы по турнирам",
)
def tournament_stats():
    return service.tournament_stats()


@router.get(
    "/teams",
    response_model=list[TeamStatOut],
    summary="Агрегация: статистика по командам",
)
def team_stats(limit: int = Query(10, ge=1, le=100)):
    return service.team_stats(limit)

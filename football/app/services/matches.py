from app import db
from app.errors import ConflictError, NotFoundError
from app.repositories import matches as repo
from app.repositories import teams as teams_repo
from app.repositories import tournaments as tournaments_repo


def _check_relations(conn, data) -> None:
    if not tournaments_repo.tournament_exists(conn, data.tournament_id):
        raise NotFoundError(f"Турнир {data.tournament_id} не найден")
    if not teams_repo.team_exists(conn, data.home_team_id):
        raise NotFoundError(f"Команда {data.home_team_id} не найдена")
    if not teams_repo.team_exists(conn, data.away_team_id):
        raise NotFoundError(f"Команда {data.away_team_id} не найдена")
    if data.home_team_id == data.away_team_id:
        raise ConflictError("Команда не может играть сама с собой")


def list_matches(status, tournament_id, team_id, date_from, date_to, page, page_size, sort):
    with db.connection() as conn:
        items, total = repo.list_matches(
            conn, status, tournament_id, team_id, date_from, date_to, page, page_size, sort
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_matches_by_team(team_id, status, page, page_size, sort):
    with db.connection() as conn:
        if not teams_repo.team_exists(conn, team_id):
            raise NotFoundError(f"Команда {team_id} не найдена")
        items, total = repo.list_matches(
            conn, status, None, team_id, None, None, page, page_size, sort
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_match(match_id):
    with db.connection() as conn:
        match = repo.get_match(conn, match_id)
    if match is None:
        raise NotFoundError(f"Матч {match_id} не найден")
    return match


def create_match(data):
    with db.connection() as conn:
        _check_relations(conn, data)
        match_id = repo.create_match(conn, data)
        return repo.get_match(conn, match_id)


def update_match(match_id, data):
    with db.connection() as conn:
        _check_relations(conn, data)
        if not repo.update_match(conn, match_id, data):
            raise NotFoundError(f"Матч {match_id} не найден")
        return repo.get_match(conn, match_id)


def delete_match(match_id):
    with db.connection() as conn:
        deleted = repo.delete_match(conn, match_id)
    if not deleted:
        raise NotFoundError(f"Матч {match_id} не найден")

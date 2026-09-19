from app import db
from app.errors import NotFoundError
from app.repositories import teams as repo
from app.repositories import tournaments as tournaments_repo


def _check_tournaments(conn, data) -> None:
    missing = set(data.tournament_ids) - tournaments_repo.existing_ids(
        conn, data.tournament_ids
    )
    if missing:
        raise NotFoundError(f"Турниры не найдены: {sorted(missing)}")


def list_teams(search, city, tournament, page, page_size, sort):
    with db.connection() as conn:
        items, total = repo.list_teams(
            conn, search, city, tournament, page, page_size, sort
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_team(team_id):
    with db.connection() as conn:
        team = repo.get_team(conn, team_id)
    if team is None:
        raise NotFoundError(f"Команда {team_id} не найдена")
    return team


def create_team(data):
    with db.connection() as conn:
        _check_tournaments(conn, data)
        team_id = repo.create_team(conn, data)
        repo.set_tournaments(conn, team_id, data.tournament_ids)
        return repo.get_team(conn, team_id)


def update_team(team_id, data):
    with db.connection() as conn:
        _check_tournaments(conn, data)
        if not repo.update_team(conn, team_id, data):
            raise NotFoundError(f"Команда {team_id} не найдена")
        repo.set_tournaments(conn, team_id, data.tournament_ids)
        return repo.get_team(conn, team_id)


def delete_team(team_id):
    with db.connection() as conn:
        deleted = repo.delete_team(conn, team_id)
    if not deleted:
        raise NotFoundError(f"Команда {team_id} не найдена")

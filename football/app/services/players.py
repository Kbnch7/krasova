from app import db
from app.errors import NotFoundError
from app.repositories import players as repo
from app.repositories import teams as teams_repo


def list_players(search, team_id, position, tournament, year_from, year_to,
                 page, page_size, sort):
    with db.connection() as conn:
        items, total = repo.list_players(
            conn, search, team_id, position, tournament, year_from, year_to,
            page, page_size, sort,
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_players_by_team(team_id, page, page_size, sort):
    with db.connection() as conn:
        if not teams_repo.team_exists(conn, team_id):
            raise NotFoundError(f"Команда {team_id} не найдена")
        items, total = repo.list_players(
            conn, None, team_id, None, None, None, None, page, page_size, sort
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_player(player_id):
    with db.connection() as conn:
        player = repo.get_player(conn, player_id)
    if player is None:
        raise NotFoundError(f"Игрок {player_id} не найден")
    return player


def create_player(data):
    with db.connection() as conn:
        if not teams_repo.team_exists(conn, data.team_id):
            raise NotFoundError(f"Команда {data.team_id} не найдена")
        player_id = repo.create_player(conn, data)
        return repo.get_player(conn, player_id)


def update_player(player_id, data):
    with db.connection() as conn:
        if not teams_repo.team_exists(conn, data.team_id):
            raise NotFoundError(f"Команда {data.team_id} не найдена")
        if not repo.update_player(conn, player_id, data):
            raise NotFoundError(f"Игрок {player_id} не найден")
        return repo.get_player(conn, player_id)


def delete_player(player_id):
    with db.connection() as conn:
        deleted = repo.delete_player(conn, player_id)
    if not deleted:
        raise NotFoundError(f"Игрок {player_id} не найден")

from app import db
from app.errors import NotFoundError
from app.repositories import events as repo
from app.repositories import matches as matches_repo
from app.repositories import players as players_repo
from app.repositories import teams as teams_repo


def list_events(event_type, match_id, player_id, team_id, tournament_id,
                date_from, date_to, page, page_size, sort):
    with db.replica_connection() as conn:
        items, total = repo.list_events(
            conn, event_type, match_id, player_id, team_id, tournament_id,
            date_from, date_to, page, page_size, sort,
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_events_by_match(match_id, event_type, page, page_size, sort):
    with db.connection() as conn:
        if not matches_repo.match_exists(conn, match_id):
            raise NotFoundError(f"Матч {match_id} не найден")
        items, total = repo.list_events(
            conn, event_type, match_id, None, None, None, None, None,
            page, page_size, sort or "minute",
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_events_by_player(player_id, event_type, page, page_size, sort):
    with db.connection() as conn:
        if not players_repo.player_exists(conn, player_id):
            raise NotFoundError(f"Игрок {player_id} не найден")
        items, total = repo.list_events(
            conn, event_type, None, player_id, None, None, None, None,
            page, page_size, sort,
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_events_by_team(team_id, event_type, page, page_size, sort):
    with db.connection() as conn:
        if not teams_repo.team_exists(conn, team_id):
            raise NotFoundError(f"Команда {team_id} не найдена")
        items, total = repo.list_events(
            conn, event_type, None, None, team_id, None, None, None,
            page, page_size, sort,
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_event(event_id):
    with db.connection() as conn:
        event = repo.get_event(conn, event_id)
    if event is None:
        raise NotFoundError(f"Событие {event_id} не найдено")
    return event


def create_event(data):
    with db.connection() as conn:
        if not matches_repo.match_exists(conn, data.match_id):
            raise NotFoundError(f"Матч {data.match_id} не найден")
        if not players_repo.player_exists(conn, data.player_id):
            raise NotFoundError(f"Игрок {data.player_id} не найден")
        return repo.create_event(
            conn, data.match_id, data.player_id, data.event_type, data.minute
        )


def update_event(event_id, data):
    with db.connection() as conn:
        event = repo.update_event(conn, event_id, data.event_type, data.minute)
    if event is None:
        raise NotFoundError(f"Событие {event_id} не найдено")
    return event


def delete_event(event_id):
    with db.connection() as conn:
        deleted = repo.delete_event(conn, event_id)
    if not deleted:
        raise NotFoundError(f"Событие {event_id} не найдено")

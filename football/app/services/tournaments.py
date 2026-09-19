import psycopg

from app import db
from app.errors import ConflictError, NotFoundError
from app.repositories import tournaments as repo


def list_tournaments():
    with db.connection() as conn:
        return repo.list_tournaments(conn)


def get_tournament(tournament_id):
    with db.connection() as conn:
        tournament = repo.get_tournament(conn, tournament_id)
    if tournament is None:
        raise NotFoundError(f"Турнир {tournament_id} не найден")
    return tournament


def create_tournament(data):
    try:
        with db.connection() as conn:
            return repo.create_tournament(conn, data)
    except psycopg.errors.UniqueViolation as exc:
        raise ConflictError(f"Турнир '{data.name}' уже существует") from exc


def update_tournament(tournament_id, data):
    try:
        with db.connection() as conn:
            tournament = repo.update_tournament(conn, tournament_id, data)
    except psycopg.errors.UniqueViolation as exc:
        raise ConflictError(f"Турнир '{data.name}' уже существует") from exc
    if tournament is None:
        raise NotFoundError(f"Турнир {tournament_id} не найден")
    return tournament


def delete_tournament(tournament_id):
    with db.connection() as conn:
        deleted = repo.delete_tournament(conn, tournament_id)
    if not deleted:
        raise NotFoundError(f"Турнир {tournament_id} не найден")

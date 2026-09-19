from app import db
from app.repositories import reports as repo


def top_scorers(date_from, date_to, tournament_id, limit):
    with db.connection() as conn:
        return repo.top_scorers(conn, date_from, date_to, tournament_id, limit)


def tournament_stats():
    with db.connection() as conn:
        return repo.tournament_stats(conn)


def team_stats(limit):
    with db.connection() as conn:
        return repo.team_stats(conn, limit)

import heapq
import itertools

from psycopg.conninfo import conninfo_to_dict

from app import db
from app.config import SHARD_STRATEGY, SHARD_URLS
from app.errors import NotFoundError, ShardUnavailableError
from app.repositories import events as events_repo
from app.repositories import matches as matches_repo
from app.repositories import players as players_repo
from app.repositories import shard_events as repo
from app.repositories.common import paginate
from app.sharding import router, stable_hash

ALL_SHARDS = list(range(len(SHARD_URLS)))


def _host(url: str) -> str:
    params = conninfo_to_dict(url)
    return f"{params.get('host')}:{params.get('port', 5432)}"


def list_shards():
    counts = db.query_shards(repo.count_events, partial=True)
    total = sum(counts.values())
    shards = []
    for shard, url in enumerate(SHARD_URLS):
        events = counts.get(shard)
        shards.append({
            "shard": shard,
            "host": _host(url),
            "ok": shard in counts,
            "events": events,
            "percent": round(100 * events / total, 2) if events is not None and total else None,
        })
    return {
        "strategy": SHARD_STRATEGY,
        "total": total,
        "partial": len(counts) < len(SHARD_URLS),
        "shards": shards,
    }


def route(match_id):
    return {
        "match_id": match_id,
        "hash": stable_hash(match_id),
        "strategy": SHARD_STRATEGY,
        "shard": router.get_shard(match_id),
    }


def _event_detail(event, player, match):
    return {
        **event,
        "player_name": player["full_name"],
        "team_id": player["team_id"],
        "team_name": player["team_name"],
        "tournament_id": match["tournament_id"],
        "match_started_at": match["started_at"],
        "home_team_name": match["home_team_name"],
        "away_team_name": match["away_team_name"],
    }


def list_match_events(match_id, page, page_size):
    with db.connection() as conn:
        match = matches_repo.get_match(conn, match_id)
    if match is None:
        raise NotFoundError(f"Матч {match_id} не найден")

    shard = router.get_shard(match_id)
    events, total = db.query_shard(
        shard, lambda conn: repo.list_by_match(conn, match_id, page, page_size)
    )

    with db.connection() as conn:
        players = players_repo.players_with_teams(conn, {e["player_id"] for e in events})
    items = [
        _event_detail(event, players[event["player_id"]], match)
        for event in events
        if event["player_id"] in players
    ]
    return {"shard": shard, "items": items, "total": total, "page": page, "page_size": page_size}


def list_events(event_type, match_id, player_id, date_from, date_to, page, page_size):
    shards = [router.get_shard(match_id)] if match_id else ALL_SHARDS
    limit, offset = paginate(page, page_size)
    results = db.query_shards(
        lambda conn: repo.list_events(
            conn, event_type, match_id, player_id, date_from, date_to, offset + limit
        ),
        shards,
    )
    total = sum(count for _, count in results.values())
    merged = heapq.merge(
        *(rows for rows, _ in results.values()),
        key=lambda event: (event["created_at"], event["id"]),
        reverse=True,
    )
    items = list(itertools.islice(merged, offset, offset + limit))
    return {"shards": shards, "items": items, "total": total, "page": page, "page_size": page_size}


def top_scorers(date_from, date_to, limit):
    results = db.query_shards(lambda conn: repo.player_totals(conn, date_from, date_to))

    totals = {}
    for rows in results.values():
        for row in rows:
            stats = totals.setdefault(row["player_id"], {"goals": 0, "assists": 0, "cards": 0})
            stats["goals"] += row["goals"]
            stats["assists"] += row["assists"]
            stats["cards"] += row["cards"]

    with db.connection() as conn:
        players = players_repo.players_with_teams(conn, totals.keys())
    rows = [
        {
            "player_id": player_id,
            "full_name": players[player_id]["full_name"],
            "team_name": players[player_id]["team_name"],
            **stats,
        }
        for player_id, stats in totals.items()
        if player_id in players
    ]
    rows.sort(key=lambda row: (-row["goals"], -row["assists"], row["full_name"]))
    return rows[:limit]


def get_event(event_id):
    found = db.query_shards(lambda conn: repo.get_event(conn, event_id), partial=True)
    for shard, event in found.items():
        if event is not None:
            return {**event, "shard": shard}
    failed = [shard for shard in ALL_SHARDS if shard not in found]
    if failed:
        raise ShardUnavailableError(failed)
    raise NotFoundError(f"Событие {event_id} не найдено ни на одном шарде")


def create_event(data):
    with db.connection() as conn:
        if not matches_repo.match_exists(conn, data.match_id):
            raise NotFoundError(f"Матч {data.match_id} не найден")
        if not players_repo.player_exists(conn, data.player_id):
            raise NotFoundError(f"Игрок {data.player_id} не найден")
        event_id = events_repo.next_event_id(conn)
    shard = router.get_shard(data.match_id)
    event = db.query_shard(
        shard,
        lambda conn: repo.create_event(
            conn, event_id, data.match_id, data.player_id, data.event_type, data.minute
        ),
    )
    return {**event, "shard": shard}

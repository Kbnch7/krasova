from app.repositories.common import paginate, sort_clause

SORTABLE = {
    "id": "e.id",
    "created_at": "e.created_at",
    "minute": "e.minute",
    "event_type": "e.event_type",
}

EVENT_DETAIL_SELECT = """
    select e.id,
           e.match_id,
           e.player_id,
           e.event_type,
           e.minute,
           e.created_at,
           e.updated_at,
           p.full_name as player_name,
           t.id        as team_id,
           t.name      as team_name,
           m.tournament_id,
           m.started_at as match_started_at,
           ht.name     as home_team_name,
           awt.name    as away_team_name
    from match_events e
    join matches m  on m.id  = e.match_id
    join players p  on p.id  = e.player_id
    join teams t    on t.id  = p.team_id
    join teams ht   on ht.id = m.home_team_id
    join teams awt  on awt.id = m.away_team_id
"""

EVENT_SELECT = """
    select id, match_id, player_id, event_type, minute, created_at, updated_at
    from match_events
"""

EVENT_COUNT_FROM = "from match_events e"
EVENT_COUNT_JOIN_MATCHES = "join matches m on m.id = e.match_id"
EVENT_COUNT_JOIN_PLAYERS = "join players p on p.id = e.player_id"


def list_events(conn, event_type, match_id, player_id, team_id, tournament_id,
                date_from, date_to, page, page_size, sort):
    where = []
    params: list = []

    if event_type:
        where.append("e.event_type = %s")
        params.append(event_type)
    if match_id:
        where.append("e.match_id = %s")
        params.append(match_id)
    if player_id:
        where.append("e.player_id = %s")
        params.append(player_id)
    if team_id:
        where.append("p.team_id = %s")
        params.append(team_id)
    if tournament_id:
        where.append("m.tournament_id = %s")
        params.append(tournament_id)
    if date_from:
        where.append("e.created_at >= %s")
        params.append(date_from)
    if date_to:
        where.append("e.created_at <= %s")
        params.append(date_to)

    count_from = [EVENT_COUNT_FROM]
    if tournament_id:
        count_from.append(EVENT_COUNT_JOIN_MATCHES)
    if team_id:
        count_from.append(EVENT_COUNT_JOIN_PLAYERS)

    where_sql = ("where " + " and ".join(where)) if where else ""
    order_sql = sort_clause(sort, SORTABLE, "e.created_at desc")
    limit, offset = paginate(page, page_size)

    with conn.cursor() as cur:
        cur.execute(
            f"select count(*) as total {' '.join(count_from)} {where_sql}", params
        )
        total = cur.fetchone()["total"]

        cur.execute(
            f"""
            {EVENT_DETAIL_SELECT}
            {where_sql}
            order by {order_sql}
            limit %s offset %s
            """,
            [*params, limit, offset],
        )
        return cur.fetchall(), total


def get_event(conn, event_id):
    with conn.cursor() as cur:
        cur.execute(f"{EVENT_SELECT} where id = %s", (event_id,))
        return cur.fetchone()


def create_event(conn, match_id, player_id, event_type, minute):
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into match_events (match_id, player_id, event_type, minute)
            values (%s, %s, %s, %s)
            returning id, match_id, player_id, event_type, minute, created_at, updated_at
            """,
            (match_id, player_id, event_type, minute),
        )
        return cur.fetchone()


def next_event_id(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("select nextval('match_events_id_seq') as id")
        return cur.fetchone()["id"]


def update_event(conn, event_id, event_type, minute):
    with conn.cursor() as cur:
        cur.execute(
            """
            update match_events
            set event_type = %s, minute = %s, updated_at = now()
            where id = %s
            returning id, match_id, player_id, event_type, minute, created_at, updated_at
            """,
            (event_type, minute, event_id),
        )
        return cur.fetchone()


def delete_event(conn, event_id) -> bool:
    with conn.cursor() as cur:
        cur.execute("delete from match_events where id = %s", (event_id,))
        return cur.rowcount > 0

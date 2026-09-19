from app.repositories.common import paginate

EVENT_SELECT = """
    select id, match_id, player_id, event_type, minute, created_at, updated_at
    from match_events
"""


def list_by_match(conn, match_id, page, page_size):
    limit, offset = paginate(page, page_size)
    with conn.cursor() as cur:
        cur.execute(
            "select count(*) as total from match_events where match_id = %s", (match_id,)
        )
        total = cur.fetchone()["total"]

        cur.execute(
            f"""
            {EVENT_SELECT}
            where match_id = %s
            order by minute, id
            limit %s offset %s
            """,
            (match_id, limit, offset),
        )
        return cur.fetchall(), total


def list_events(conn, event_type, match_id, player_id, date_from, date_to, limit):
    where = []
    params: list = []

    if event_type:
        where.append("event_type = %s")
        params.append(event_type)
    if match_id:
        where.append("match_id = %s")
        params.append(match_id)
    if player_id:
        where.append("player_id = %s")
        params.append(player_id)
    if date_from:
        where.append("created_at >= %s")
        params.append(date_from)
    if date_to:
        where.append("created_at <= %s")
        params.append(date_to)

    where_sql = ("where " + " and ".join(where)) if where else ""

    with conn.cursor() as cur:
        cur.execute(f"select count(*) as total from match_events {where_sql}", params)
        total = cur.fetchone()["total"]

        cur.execute(
            f"""
            {EVENT_SELECT}
            {where_sql}
            order by created_at desc, id desc
            limit %s
            """,
            [*params, limit],
        )
        return cur.fetchall(), total


def player_totals(conn, date_from, date_to):
    where = []
    params: list = []
    if date_from:
        where.append("created_at >= %s")
        params.append(date_from)
    if date_to:
        where.append("created_at <= %s")
        params.append(date_to)
    where_sql = ("where " + " and ".join(where)) if where else ""

    with conn.cursor() as cur:
        cur.execute(
            f"""
            select player_id,
                   count(*) filter (where event_type = 'GOAL')   as goals,
                   count(*) filter (where event_type = 'ASSIST') as assists,
                   count(*) filter (
                       where event_type in ('YELLOW_CARD', 'RED_CARD')
                   )                                             as cards
            from match_events
            {where_sql}
            group by player_id
            """,
            params,
        )
        return cur.fetchall()


def get_event(conn, event_id):
    with conn.cursor() as cur:
        cur.execute(f"{EVENT_SELECT} where id = %s", (event_id,))
        return cur.fetchone()


def create_event(conn, event_id, match_id, player_id, event_type, minute):
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into match_events (id, match_id, player_id, event_type, minute)
            values (%s, %s, %s, %s, %s)
            returning id, match_id, player_id, event_type, minute, created_at, updated_at
            """,
            (event_id, match_id, player_id, event_type, minute),
        )
        return cur.fetchone()


def count_events(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("select count(*) as total from match_events")
        return cur.fetchone()["total"]

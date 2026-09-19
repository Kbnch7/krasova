from app.repositories.common import paginate, sort_clause

SORTABLE = {
    "id": "m.id",
    "started_at": "m.started_at",
    "created_at": "m.created_at",
    "status": "m.status",
    "tournament": "tr.name",
}

MATCH_SELECT = """
    select m.id,
           m.tournament_id,
           tr.name  as tournament_name,
           m.home_team_id,
           ht.name  as home_team_name,
           m.away_team_id,
           awt.name as away_team_name,
           m.status,
           m.started_at,
           m.home_score,
           m.away_score,
           m.created_at
    from matches m
    join tournaments tr on tr.id = m.tournament_id
    join teams ht  on ht.id  = m.home_team_id
    join teams awt on awt.id = m.away_team_id
"""

MATCH_COUNT_FROM = """
    from matches m
    join tournaments tr on tr.id = m.tournament_id
"""


def list_matches(conn, status, tournament_id, team_id, date_from, date_to,
                 page, page_size, sort):
    where = []
    params: list = []

    if status:
        where.append("m.status = %s")
        params.append(status)
    if tournament_id:
        where.append("m.tournament_id = %s")
        params.append(tournament_id)
    if team_id:
        where.append("(m.home_team_id = %s or m.away_team_id = %s)")
        params.extend([team_id, team_id])
    if date_from:
        where.append("m.started_at >= %s")
        params.append(date_from)
    if date_to:
        where.append("m.started_at <= %s")
        params.append(date_to)

    where_sql = ("where " + " and ".join(where)) if where else ""
    order_sql = sort_clause(sort, SORTABLE, "m.started_at desc")
    limit, offset = paginate(page, page_size)

    with conn.cursor() as cur:
        cur.execute(
            f"select count(*) as total {MATCH_COUNT_FROM} {where_sql}", params
        )
        total = cur.fetchone()["total"]

        cur.execute(
            f"""
            {MATCH_SELECT}
            {where_sql}
            order by {order_sql}
            limit %s offset %s
            """,
            [*params, limit, offset],
        )
        return cur.fetchall(), total


def get_match(conn, match_id):
    with conn.cursor() as cur:
        cur.execute(f"{MATCH_SELECT} where m.id = %s", (match_id,))
        return cur.fetchone()


def create_match(conn, data) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into matches (tournament_id, home_team_id, away_team_id,
                                 status, started_at, home_score, away_score)
            values (%s, %s, %s, %s, %s, %s, %s)
            returning id
            """,
            (
                data.tournament_id,
                data.home_team_id,
                data.away_team_id,
                data.status,
                data.started_at,
                data.home_score,
                data.away_score,
            ),
        )
        return cur.fetchone()["id"]


def update_match(conn, match_id, data) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            update matches
            set tournament_id = %s, home_team_id = %s, away_team_id = %s,
                status = %s, started_at = %s, home_score = %s, away_score = %s
            where id = %s
            """,
            (
                data.tournament_id,
                data.home_team_id,
                data.away_team_id,
                data.status,
                data.started_at,
                data.home_score,
                data.away_score,
                match_id,
            ),
        )
        return cur.rowcount > 0


def delete_match(conn, match_id) -> bool:
    with conn.cursor() as cur:
        cur.execute("delete from matches where id = %s", (match_id,))
        return cur.rowcount > 0


def match_exists(conn, match_id) -> bool:
    with conn.cursor() as cur:
        cur.execute("select 1 from matches where id = %s", (match_id,))
        return cur.fetchone() is not None

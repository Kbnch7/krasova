from app.repositories.common import paginate, sort_clause

SORTABLE = {
    "id": "t.id",
    "name": "t.name",
    "city": "t.city",
    "founded_year": "t.founded_year",
    "created_at": "t.created_at",
}

TEAM_SELECT = """
    select t.id,
           t.name,
           t.city,
           t.founded_year,
           t.created_at,
           coalesce(
               array_agg(tr.name order by tr.name) filter (where tr.id is not null),
               '{}'
           ) as tournaments
    from teams t
    left join team_tournaments tt on tt.team_id = t.id
    left join tournaments tr      on tr.id = tt.tournament_id
"""


def list_teams(conn, search, city, tournament, page, page_size, sort):
    where = []
    params: list = []

    if search:
        where.append("t.name ilike %s")
        params.append(f"%{search}%")
    if city:
        where.append("t.city = %s")
        params.append(city)
    if tournament:
        where.append(
            """exists (
                   select 1
                   from team_tournaments tt2
                   join tournaments tr2 on tr2.id = tt2.tournament_id
                   where tt2.team_id = t.id and tr2.name ilike %s
               )"""
        )
        params.append(tournament)

    where_sql = ("where " + " and ".join(where)) if where else ""
    order_sql = sort_clause(sort, SORTABLE, "t.id asc")
    limit, offset = paginate(page, page_size)

    with conn.cursor() as cur:
        cur.execute(f"select count(*) as total from teams t {where_sql}", params)
        total = cur.fetchone()["total"]

        cur.execute(
            f"""
            {TEAM_SELECT}
            {where_sql}
            group by t.id
            order by {order_sql}
            limit %s offset %s
            """,
            [*params, limit, offset],
        )
        return cur.fetchall(), total


def get_team(conn, team_id):
    with conn.cursor() as cur:
        cur.execute(
            f"""
            {TEAM_SELECT}
            where t.id = %s
            group by t.id
            """,
            (team_id,),
        )
        return cur.fetchone()


def create_team(conn, data) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into teams (name, city, founded_year)
            values (%s, %s, %s)
            returning id
            """,
            (data.name, data.city, data.founded_year),
        )
        return cur.fetchone()["id"]


def update_team(conn, team_id, data) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            update teams
            set name = %s, city = %s, founded_year = %s
            where id = %s
            """,
            (data.name, data.city, data.founded_year, team_id),
        )
        return cur.rowcount > 0


def delete_team(conn, team_id) -> bool:
    with conn.cursor() as cur:
        cur.execute("delete from teams where id = %s", (team_id,))
        return cur.rowcount > 0


def team_exists(conn, team_id) -> bool:
    with conn.cursor() as cur:
        cur.execute("select 1 from teams where id = %s", (team_id,))
        return cur.fetchone() is not None


def set_tournaments(conn, team_id: int, tournament_ids: list[int]) -> None:
    with conn.cursor() as cur:
        cur.execute("delete from team_tournaments where team_id = %s", (team_id,))
        for tournament_id in set(tournament_ids):
            cur.execute(
                "insert into team_tournaments (team_id, tournament_id) values (%s, %s)",
                (team_id, tournament_id),
            )

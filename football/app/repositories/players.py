from app.repositories.common import paginate, sort_clause

SORTABLE = {
    "id": "p.id",
    "full_name": "p.full_name",
    "birth_year": "p.birth_year",
    "shirt_number": "p.shirt_number",
    "created_at": "p.created_at",
    "team": "t.name",
}

PLAYER_SELECT = """
    select p.id,
           p.full_name,
           p.team_id,
           t.name as team_name,
           t.city as team_city,
           p.position,
           p.birth_year,
           p.shirt_number,
           p.created_at,
           coalesce(
               array_agg(tr.name order by tr.name) filter (where tr.id is not null),
               '{}'
           ) as tournaments
    from players p
    join teams t on t.id = p.team_id
    left join team_tournaments tt on tt.team_id = t.id
    left join tournaments tr on tr.id = tt.tournament_id
"""


def list_players(conn, search, team_id, position, tournament, year_from, year_to,
                 page, page_size, sort):
    where = []
    params: list = []

    if search:
        where.append("(p.full_name ilike %s or t.name ilike %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    if team_id:
        where.append("p.team_id = %s")
        params.append(team_id)
    if position:
        where.append("p.position = %s")
        params.append(position)
    if tournament:
        where.append(
            """exists (
                   select 1
                   from team_tournaments tt2
                   join tournaments tr2 on tr2.id = tt2.tournament_id
                   where tt2.team_id = p.team_id and tr2.name ilike %s
               )"""
        )
        params.append(tournament)
    if year_from:
        where.append("p.birth_year >= %s")
        params.append(year_from)
    if year_to:
        where.append("p.birth_year <= %s")
        params.append(year_to)

    where_sql = ("where " + " and ".join(where)) if where else ""
    order_sql = sort_clause(sort, SORTABLE, "p.id asc")
    limit, offset = paginate(page, page_size)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            select count(*) as total
            from players p
            join teams t on t.id = p.team_id
            {where_sql}
            """,
            params,
        )
        total = cur.fetchone()["total"]

        cur.execute(
            f"""
            {PLAYER_SELECT}
            {where_sql}
            group by p.id, t.name, t.city
            order by {order_sql}
            limit %s offset %s
            """,
            [*params, limit, offset],
        )
        return cur.fetchall(), total


def get_player(conn, player_id):
    with conn.cursor() as cur:
        cur.execute(
            f"""
            {PLAYER_SELECT}
            where p.id = %s
            group by p.id, t.name, t.city
            """,
            (player_id,),
        )
        return cur.fetchone()


def create_player(conn, data) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into players (full_name, team_id, position, birth_year, shirt_number)
            values (%s, %s, %s, %s, %s)
            returning id
            """,
            (data.full_name, data.team_id, data.position, data.birth_year, data.shirt_number),
        )
        return cur.fetchone()["id"]


def update_player(conn, player_id, data) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            update players
            set full_name = %s, team_id = %s, position = %s,
                birth_year = %s, shirt_number = %s
            where id = %s
            """,
            (
                data.full_name,
                data.team_id,
                data.position,
                data.birth_year,
                data.shirt_number,
                player_id,
            ),
        )
        return cur.rowcount > 0


def delete_player(conn, player_id) -> bool:
    with conn.cursor() as cur:
        cur.execute("delete from players where id = %s", (player_id,))
        return cur.rowcount > 0


def player_exists(conn, player_id) -> bool:
    with conn.cursor() as cur:
        cur.execute("select 1 from players where id = %s", (player_id,))
        return cur.fetchone() is not None


def players_with_teams(conn, player_ids) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            select p.id, p.full_name, t.id as team_id, t.name as team_name
            from players p
            join teams t on t.id = p.team_id
            where p.id = any(%s)
            """,
            (list(player_ids),),
        )
        return {row["id"]: row for row in cur.fetchall()}

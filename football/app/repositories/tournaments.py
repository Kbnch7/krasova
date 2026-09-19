def list_tournaments(conn):
    with conn.cursor() as cur:
        cur.execute("select id, name, season from tournaments order by name")
        return cur.fetchall()


def get_tournament(conn, tournament_id):
    with conn.cursor() as cur:
        cur.execute(
            "select id, name, season from tournaments where id = %s", (tournament_id,)
        )
        return cur.fetchone()


def create_tournament(conn, data):
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into tournaments (name, season)
            values (%s, %s)
            returning id, name, season
            """,
            (data.name, data.season),
        )
        return cur.fetchone()


def update_tournament(conn, tournament_id, data):
    with conn.cursor() as cur:
        cur.execute(
            """
            update tournaments
            set name = %s, season = %s
            where id = %s
            returning id, name, season
            """,
            (data.name, data.season, tournament_id),
        )
        return cur.fetchone()


def delete_tournament(conn, tournament_id) -> bool:
    with conn.cursor() as cur:
        cur.execute("delete from tournaments where id = %s", (tournament_id,))
        return cur.rowcount > 0


def existing_ids(conn, tournament_ids: list[int]) -> set[int]:
    if not tournament_ids:
        return set()
    with conn.cursor() as cur:
        cur.execute(
            "select id from tournaments where id = any(%s)", (list(tournament_ids),)
        )
        return {row["id"] for row in cur.fetchall()}


def tournament_exists(conn, tournament_id) -> bool:
    with conn.cursor() as cur:
        cur.execute("select 1 from tournaments where id = %s", (tournament_id,))
        return cur.fetchone() is not None

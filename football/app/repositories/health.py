def ping(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("select 1")
        cur.fetchone()

from psycopg import sql


def table_identifier(table: str) -> sql.Identifier:
    return sql.Identifier(*table.split("."))


def list_partitions(conn, table: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select c.relname as name
            from pg_inherits i
            join pg_class c on c.oid = i.inhrelid
            where i.inhparent = %s::regclass
            order by c.relname
            """,
            (table,),
        )
        return [row["name"] for row in cur.fetchall()]


def create_partition(conn, table: str, name: str, start: str, end: str) -> None:
    schema = table.split(".")[:-1]
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                "create table {} partition of {} for values from ({}) to ({})"
            ).format(
                sql.Identifier(*schema, name),
                table_identifier(table),
                sql.Literal(start),
                sql.Literal(end),
            )
        )


def get_alert_status(conn, table: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "select status from partition_alerts where table_name = %s", (table,)
        )
        row = cur.fetchone()
        return row["status"] if row else None


def save_alert_status(conn, table: str, status: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into partition_alerts (table_name, status, changed_at)
            values (%s, %s, now())
            on conflict (table_name)
            do update set status = excluded.status, changed_at = now()
            """,
            (table, status),
        )

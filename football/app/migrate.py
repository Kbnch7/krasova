import pathlib
import sys
import time

import psycopg

from app.config import DATABASE_URL, SHARD_URLS

SQL_DIR = pathlib.Path(__file__).resolve().parent.parent / "sql"
MIGRATIONS_DIR = SQL_DIR / "migrations"
SHARD_MIGRATIONS_DIR = SQL_DIR / "shard_migrations"


def wait_for_db(url: str, attempts: int = 30, delay: float = 2.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            with psycopg.connect(url, connect_timeout=3):
                return
        except psycopg.OperationalError as exc:
            print(f"[migrate] БД недоступна ({attempt}/{attempts}): {exc}")
            time.sleep(delay)
    print("[migrate] не удалось дождаться PostgreSQL")
    sys.exit(1)


def applied_migrations(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            create table if not exists schema_migrations (
                name        text primary key,
                applied_at  timestamptz not null default now()
            )
            """
        )
        cur.execute("select name from schema_migrations")
        return {row[0] for row in cur.fetchall()}


def migrate(url: str, directory: pathlib.Path, label: str) -> None:
    wait_for_db(url)

    with psycopg.connect(url) as conn:
        done = applied_migrations(conn)
        conn.commit()

        files = sorted(directory.glob("*.sql"))
        for path in files:
            if path.name in done:
                continue
            print(f"[migrate] {label}: применяю {path.name}")
            with conn.cursor() as cur:
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    "insert into schema_migrations (name) values (%s)", (path.name,)
                )
            conn.commit()

        print(f"[migrate] {label}: готово, всего миграций: {len(files)}")


def main() -> None:
    migrate(DATABASE_URL, MIGRATIONS_DIR, "primary")
    for shard, url in enumerate(SHARD_URLS):
        migrate(url, SHARD_MIGRATIONS_DIR, f"shard_{shard}")


if __name__ == "__main__":
    main()

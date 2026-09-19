import pathlib

import psycopg

from app.config import DATABASE_URL

SEED_FILE = pathlib.Path(__file__).resolve().parent.parent / "sql" / "seed.sql"


def main() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("select count(*) from teams")
            if cur.fetchone()[0] > 0:
                print("[seed] данные уже есть, пропускаю")
                return
            print("[seed] заливаю тестовые данные")
            cur.execute(SEED_FILE.read_text(encoding="utf-8"))
        conn.commit()
        print("[seed] готово")


if __name__ == "__main__":
    main()

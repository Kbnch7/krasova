import os
import time

import psycopg

PRIMARY_URL = os.getenv("DATABASE_URL", "postgresql://football:football@localhost:5436/football")
REPLICA_URL = os.getenv("REPLICA_DATABASE_URL", "postgresql://football:football@localhost:5437/football")
ROUNDS = 1000
BIG_ROWS = 2_000_000


def wait_marker(replica, expected):
    started = time.perf_counter()
    checks = 0
    while True:
        checks += 1
        try:
            row = replica.execute("select v from lab4.lag_test where id = 1").fetchone()
        except psycopg.errors.UndefinedTable:
            row = None
        if row is not None and row[0] == expected:
            return checks, (time.perf_counter() - started) * 1000


def prepare(primary, replica):
    primary.execute("create schema if not exists lab4")
    primary.execute("create table if not exists lab4.lag_test (id int primary key, v int not null)")
    primary.execute("insert into lab4.lag_test values (1, 0) on conflict (id) do update set v = 0")
    wait_marker(replica, 0)


def small_updates(primary, replica):
    stale = []
    for i in range(1, ROUNDS + 1):
        primary.execute("update lab4.lag_test set v = %s where id = 1", (i,))
        checks, ms = wait_marker(replica, i)
        if checks > 1:
            stale.append(ms)
    print(f"маленький update на primary и сразу select на реплике, раз: {ROUNDS}")
    print(f"реплика отдала старое значение, раз: {len(stale)}")
    if stale:
        print(
            f"новое значение появилось на реплике через: min {min(stale):.2f} ms, "
            f"avg {sum(stale) / len(stale):.2f} ms, max {max(stale):.2f} ms"
        )


def big_update(primary, replica):
    primary.execute("drop table if exists lab4.lag_big")
    primary.execute(
        f"create table lab4.lag_big as select g as id, 0 as v from generate_series(1, {BIG_ROWS}) g"
    )
    primary.execute("update lab4.lag_test set v = 0 where id = 1")
    wait_marker(replica, 0)

    started = time.perf_counter()
    with primary.transaction():
        primary.execute("update lab4.lag_big set v = 1")
        primary.execute("update lab4.lag_test set v = -1 where id = 1")
    commit_ms = (time.perf_counter() - started) * 1000
    behind, replay_lag = primary.execute(
        "select pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn), replay_lag from pg_stat_replication"
    ).fetchone()
    checks, ms = wait_marker(replica, -1)
    updated = replica.execute("select count(*) from lab4.lag_big where v = 1").fetchone()[0]

    print(f"update {BIG_ROWS} строк одной транзакцией на primary: {commit_ms:.0f} ms")
    print(f"сразу после commit реплика отставала на {int(behind)} байт wal, replay_lag {replay_lag}")
    print(f"select на реплике сразу после commit видел старые данные: {'да' if checks > 1 else 'нет'}")
    print(f"новые данные появились на реплике через {ms:.1f} ms, проверок {checks}")
    print(f"на реплике строк с v = 1: {updated}")
    primary.execute("drop table lab4.lag_big")


def main() -> None:
    with psycopg.connect(PRIMARY_URL, autocommit=True) as primary, \
            psycopg.connect(REPLICA_URL, autocommit=True) as replica:
        prepare(primary, replica)
        small_updates(primary, replica)
        big_update(primary, replica)


if __name__ == "__main__":
    main()

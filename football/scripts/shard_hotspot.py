import random
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import psycopg

from app.config import DATABASE_URL, SHARD_URLS
from app.sharding import router

API = "http://127.0.0.1:8000"
REQUESTS = 3000
WORKERS = 16
HOT_MATCH = 7
HOT_SHARE = 0.6


def shard_stats():
    stats = []
    for url in SHARD_URLS:
        with psycopg.connect(url) as conn:
            stats.append(conn.execute(
                """
                select xact_commit, tup_returned + tup_fetched
                from pg_stat_database
                where datname = current_database()
                """
            ).fetchone())
    return stats


def shard_rows():
    rows = []
    for url in SHARD_URLS:
        with psycopg.connect(url) as conn:
            rows.append(conn.execute("select count(*) from match_events").fetchone()[0])
    return rows


def call(match_id):
    started = time.perf_counter()
    with urllib.request.urlopen(f"{API}/api/shards/matches/{match_id}/events?page_size=20") as resp:
        resp.read()
    return router.get_shard(match_id), time.perf_counter() - started


def percents(values):
    total = sum(values)
    return [100 * value / total for value in values]


def run(title, match_ids):
    before = shard_stats()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        results = list(executor.map(call, match_ids))
    elapsed = time.perf_counter() - started
    time.sleep(11)
    after = shard_stats()

    shards = range(len(SHARD_URLS))
    routed = [sum(1 for shard, _ in results if shard == s) for s in shards]
    xacts = [after[s][0] - before[s][0] for s in shards]
    tuples = [after[s][1] - before[s][1] for s in shards]
    latency = [
        statistics.median(1000 * t for shard, t in results if shard == s) if routed[s] else 0
        for s in shards
    ]

    print(f"\n== {title}: {len(match_ids)} запросов за {elapsed:.1f} s, {WORKERS} потоков ==")
    print(f"{'':8}{'запросов':>10}{'%':>8}{'транзакций':>12}{'%':>8}{'строк прочитано':>17}{'%':>8}{'медиана':>10}")
    for s in shards:
        print(
            f"shard {s} {routed[s]:>9}{percents(routed)[s]:>7.1f}%{xacts[s]:>12}{percents(xacts)[s]:>7.1f}%"
            f"{tuples[s]:>17}{percents(tuples)[s]:>7.1f}%{latency[s]:>8.0f} ms"
        )


def main() -> None:
    random.seed(6)
    with psycopg.connect(DATABASE_URL) as conn:
        match_ids = [row[0] for row in conn.execute("select id from matches")]

    rows = shard_rows()
    print("строк на шардах: " + ", ".join(
        f"shard {s} {count} ({share:.1f}%)" for s, (count, share) in enumerate(zip(rows, percents(rows)))
    ))
    print(f"горячий матч {HOT_MATCH} лежит на shard {router.get_shard(HOT_MATCH)}")

    run("обычный день, матчи случайные", [random.choice(match_ids) for _ in range(REQUESTS)])
    run(
        f"финал, {HOT_SHARE:.0%} запросов про матч {HOT_MATCH}",
        [HOT_MATCH if random.random() < HOT_SHARE else random.choice(match_ids) for _ in range(REQUESTS)],
    )


if __name__ == "__main__":
    main()

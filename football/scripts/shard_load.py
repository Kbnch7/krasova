import argparse
import contextlib
import time

import psycopg

from app.config import DATABASE_URL, SHARD_STRATEGY, SHARD_URLS, SHARD_VNODES
from app.sharding import make_router

COLUMNS = "id, match_id, player_id, event_type, minute, created_at, updated_at"


def load(router) -> int:
    shards = [psycopg.connect(url) for url in SHARD_URLS]
    for conn in shards:
        conn.execute("truncate match_events")

    routes = {}
    loaded = 0
    with psycopg.connect(DATABASE_URL) as primary, contextlib.ExitStack() as stack:
        copies = [
            stack.enter_context(conn.cursor().copy(f"copy match_events ({COLUMNS}) from stdin"))
            for conn in shards
        ]
        with primary.cursor(name="shard_load") as source:
            source.itersize = 20000
            source.execute(f"select {COLUMNS} from match_events")
            for row in source:
                match_id = row[1]
                shard = routes.get(match_id)
                if shard is None:
                    shard = routes[match_id] = router.get_shard(match_id)
                copies[shard].write_row(row)
                loaded += 1

    for conn in shards:
        conn.commit()
        conn.close()
    return loaded


def report() -> None:
    counts = []
    for url in SHARD_URLS:
        with psycopg.connect(url) as conn:
            counts.append(
                conn.execute("select count(*), count(distinct match_id) from match_events").fetchone()
            )

    total = sum(events for events, _ in counts)
    ideal = total / len(counts)
    for shard, (events, matches) in enumerate(counts):
        print(
            f"shard {shard} → {events} записей ({100 * events / total:.2f} %), "
            f"от идеала {100 * (events - ideal) / ideal:+.2f} %, матчей {matches}"
        )
    biggest = max(events for events, _ in counts)
    smallest = min(events for events, _ in counts)
    print(f"всего {total}, идеально по {ideal:.0f} на шард")
    print(f"самый большой шард больше самого маленького в {biggest / smallest:.3f} раза")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=["mod", "ring"], default=SHARD_STRATEGY)
    args = parser.parse_args()

    router = make_router(args.strategy)
    vnodes = f", vnodes {SHARD_VNODES}" if args.strategy == "ring" else ""
    print(f"стратегия {args.strategy}{vnodes}, шардов {len(SHARD_URLS)}")

    started = time.perf_counter()
    loaded = load(router)
    print(f"загружено {loaded} событий за {time.perf_counter() - started:.1f} s")
    report()


if __name__ == "__main__":
    main()

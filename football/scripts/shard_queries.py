import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import psycopg

from app.config import DATABASE_URL, SHARD_URLS

TOTALS_SQL = """
    select player_id,
           count(*) filter (where event_type = 'GOAL')   as goals,
           count(*) filter (where event_type = 'ASSIST') as assists
    from match_events
    group by player_id
"""

TOP_SQL = TOTALS_SQL + " order by goals desc, assists desc, player_id limit %s"


def timed(fn, repeat=3):
    times = []
    for _ in range(repeat):
        started = time.perf_counter()
        result = fn()
        times.append(1000 * (time.perf_counter() - started))
    return result, statistics.median(times)


def fetch(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


def sequential(conns, sql, params=()):
    return [fetch(conn, sql, params) for conn in conns]


def parallel(conns, sql, params=()):
    with ThreadPoolExecutor(max_workers=len(conns)) as executor:
        return list(executor.map(lambda conn: fetch(conn, sql, params), conns))


def add_totals(parts):
    totals = {}
    for rows in parts:
        for player_id, goals, assists in rows:
            old = totals.get(player_id, (0, 0))
            totals[player_id] = (old[0] + goals, old[1] + assists)
    return sorted(totals.items(), key=lambda item: (-item[1][0], -item[1][1], item[0]))


def count_all(primary, shards):
    print("== 1. count(*) по всем шардам ==")
    (row,), ms = timed(lambda: fetch(primary, "select count(*) from match_events"))
    print(f"primary одним запросом: {row[0]} за {ms:.0f} ms")
    parts, ms_seq = timed(lambda: sequential(shards, "select count(*) from match_events"))
    for shard, rows in enumerate(parts):
        print(f"shard {shard} → {rows[0][0]}")
    print(f"сумма в backend: {sum(rows[0][0] for rows in parts)}")
    _, ms_par = timed(lambda: parallel(shards, "select count(*) from match_events"))
    print(f"шарды по очереди: {ms_seq:.0f} ms, параллельно: {ms_par:.0f} ms")


def avg_and_distinct(primary, shards):
    print("\n== 2. avg и count(distinct) ==")
    sql = "select count(*), count(distinct match_id), count(distinct player_id) from match_events"
    (real,) = fetch(primary, sql)
    parts = [rows[0] for rows in parallel(shards, sql)]
    for shard, (events, matches, players) in enumerate(parts):
        print(f"shard {shard}: событий {events}, матчей {matches}, игроков {players}, "
              f"событий на матч {events / matches:.4f}")
    events = sum(part[0] for part in parts)
    matches = sum(part[1] for part in parts)
    avg_of_avg = sum(part[0] / part[1] for part in parts) / len(parts)
    print(f"событий на матч на primary:           {real[0] / real[1]:.4f}")
    print(f"сумма событий / сумма матчей:         {events / matches:.4f}")
    print(f"среднее из средних трех шардов:       {avg_of_avg:.4f}")
    print(f"матчей: сумма по шардам {matches}, на primary {real[1]}")
    print(f"игроков: сумма по шардам {sum(part[2] for part in parts)}, на primary {real[2]}")


def top_scorers(primary, shards, limit=10):
    print(f"\n== 3. top {limit} бомбардиров ==")
    (real, ms_primary) = timed(lambda: fetch(primary, TOP_SQL, (limit,)), repeat=1)
    correct_parts, ms_shards = timed(lambda: parallel(shards, TOTALS_SQL), repeat=1)
    correct = add_totals(correct_parts)[:limit]
    naive_parts = parallel(shards, TOP_SQL, (limit,))
    naive = add_totals(naive_parts)[:limit]
    rows_moved = sum(len(rows) for rows in correct_parts)
    print(f"primary: {ms_primary:.0f} ms; шарды параллельно: {ms_shards:.0f} ms, "
          f"в backend пришло {rows_moved} строк (частичные суммы по игрокам)")
    print(f"с primary совпало: {[r[0] for r in real] == [p for p, _ in correct]}")
    print(f"{'место':>5} {'правильно':>10} {'голов':>6}   {'наивно':>8} {'голов':>6}")
    for place, ((player, (goals, _)), (naive_player, (naive_goals, _))) in enumerate(zip(correct, naive), 1):
        mark = "" if player == naive_player and goals == naive_goals else "  ✗"
        print(f"{place:>5} {player:>10} {goals:>6}   {naive_player:>8} {naive_goals:>6}{mark}")
    same = len({p for p, _ in correct} & {p for p, _ in naive})
    print(f"одинаковых игроков в двух списках: {same} из {limit}")
    leader = correct[0][0]
    by_shard = [dict((p, g) for p, g, _ in rows).get(leader, 0) for rows in correct_parts]
    print(f"голы лидера {leader} по шардам: {by_shard} = {sum(by_shard)}")


def order_limit(shards, limit=100):
    print(f"\n== 4. order by created_at desc limit {limit} ==")
    sql = "select id, created_at from match_events order by created_at desc, id desc limit %s"
    parts, ms = timed(lambda: parallel(shards, sql, (limit,)))
    tagged = sorted(
        ((created_at, event_id, shard) for shard, rows in enumerate(parts) for event_id, created_at in rows),
        reverse=True,
    )[:limit]
    print(f"top {limit} с каждого шарда и merge: {ms:.0f} ms, в backend пришло {sum(map(len, parts))} строк")
    for shard, rows in enumerate(parts):
        taken = sum(1 for *_, s in tagged if s == shard)
        print(f"shard {shard}: свой top {limit} от {rows[-1][1]:%Y-%m-%d %H:%M} до {rows[0][1]:%Y-%m-%d %H:%M}, "
              f"в общий top {limit} попало {taken}")
    print(f"общий top {limit}: от {tagged[-1][0]:%Y-%m-%d %H:%M} до {tagged[0][0]:%Y-%m-%d %H:%M}")


def shards_count_time(shards, player_id=5832):
    print("\n== 5. время запроса от числа шардов ==")
    sql = "select count(*) from match_events where player_id = %s"
    print(f"{'шардов':>6} {'по очереди':>11} {'параллельно':>12}")
    for n in range(1, len(shards) + 1):
        _, ms_seq = timed(lambda: sequential(shards[:n], sql, (player_id,)), repeat=5)
        _, ms_par = timed(lambda: parallel(shards[:n], sql, (player_id,)), repeat=5)
        print(f"{n:>6} {ms_seq:>9.0f} ms {ms_par:>10.0f} ms")


def main() -> None:
    with psycopg.connect(DATABASE_URL) as primary:
        shards = [psycopg.connect(url, autocommit=True) for url in SHARD_URLS]
        primary.autocommit = True
        count_all(primary, shards)
        avg_and_distinct(primary, shards)
        top_scorers(primary, shards)
        order_limit(shards)
        shards_count_time(shards)
        for conn in shards:
            conn.close()


if __name__ == "__main__":
    main()

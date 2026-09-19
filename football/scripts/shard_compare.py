import psycopg

from app.config import SHARD_URLS, SHARD_VNODES
from app.sharding import HashRing, ModRouter


def load_counts() -> dict[int, int]:
    counts = {}
    for url in SHARD_URLS:
        with psycopg.connect(url) as conn:
            rows = conn.execute("select match_id, count(*) from match_events group by match_id")
            for match_id, events in rows:
                counts[match_id] = counts.get(match_id, 0) + events
    return counts


def compare(counts, old, new):
    flows = {}
    moved_events = 0
    moved_matches = 0
    for match_id, events in counts.items():
        before = old.get_shard(match_id)
        after = new.get_shard(match_id)
        flows[(before, after)] = flows.get((before, after), 0) + events
        if before != after:
            moved_events += events
            moved_matches += 1
    return moved_events, moved_matches, flows


def shares(counts, router, shards) -> list[float]:
    sizes = dict.fromkeys(shards, 0)
    for match_id, events in counts.items():
        sizes[router.get_shard(match_id)] += events
    total = sum(sizes.values())
    return [100 * sizes[shard] / total for shard in shards]


def scenario(title, counts, old, new, old_shards, new_shards) -> float:
    total = sum(counts.values())
    moved, moved_matches, flows = compare(counts, old, new)
    print(f"\n== {title} ==")
    print(f"всего записей: {total}")
    print(f"изменили shard: {moved} ({100 * moved / total:.2f} %)")
    print(f"не изменили: {total - moved} ({100 * (total - moved) / total:.2f} %)")
    print(f"матчей переехало: {moved_matches} из {len(counts)}")
    print("откуда → куда, записей:")
    print("        " + "".join(f"{'→ ' + str(shard):>11}" for shard in new_shards))
    for before in old_shards:
        cells = "".join(f"{flows.get((before, after), 0):>11}" for after in new_shards)
        print(f"из {before}    {cells}")
    return 100 * moved / total


def main() -> None:
    counts = load_counts()
    print(f"данные с шардов: {sum(counts.values())} записей, {len(counts)} матчей")

    three = [0, 1, 2]
    four = [0, 1, 2, 3]
    five = [0, 1, 2, 3, 4]
    without_1 = [0, 2]
    v = SHARD_VNODES

    mod_34 = scenario("hash(key) % N: 3 → 4", counts, ModRouter(three), ModRouter(four), three, four)
    ring_34 = scenario(
        f"consistent hashing, vnodes {v}: 3 → 4",
        counts, HashRing(three, v), HashRing(four, v), three, four,
    )
    mod_45 = scenario("hash(key) % N: 4 → 5", counts, ModRouter(four), ModRouter(five), four, five)
    ring_45 = scenario(
        f"consistent hashing, vnodes {v}: 4 → 5",
        counts, HashRing(four, v), HashRing(five, v), four, five,
    )
    mod_del = scenario(
        "hash(key) % N: удалили shard 1", counts, ModRouter(three), ModRouter(without_1), three, without_1
    )
    ring_del = scenario(
        f"consistent hashing, vnodes {v}: удалили shard 1",
        counts, HashRing(three, v), HashRing(without_1, v), three, without_1,
    )

    print("\n== итог ==")
    print(f"{'':28}{'3 → 4':>10}{'4 → 5':>10}{'удалили 1':>12}")
    print(f"{'hash(key) % N':28}{mod_34:>9.2f}%{mod_45:>9.2f}%{mod_del:>11.2f}%")
    print(f"{'consistent hashing':28}{ring_34:>9.2f}%{ring_45:>9.2f}%{ring_del:>11.2f}%")

    print("\n== виртуальные узлы ==")
    print(f"{'vnodes':>7}  {'shard 0':>8}{'shard 1':>9}{'shard 2':>9}  {'3 → 4 перемещено':>17}  {'shard 3 после':>14}")
    for vnodes in (1, 3, 10, 100, 1000):
        old = HashRing(three, vnodes)
        new = HashRing(four, vnodes)
        parts = shares(counts, old, three)
        moved, _, _ = compare(counts, old, new)
        new_part = shares(counts, new, four)[3]
        print(
            f"{vnodes:>7}  {parts[0]:>7.2f}%{parts[1]:>8.2f}%{parts[2]:>8.2f}%"
            f"  {100 * moved / sum(counts.values()):>16.2f}%  {new_part:>13.2f}%"
        )


if __name__ == "__main__":
    main()

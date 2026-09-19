import bisect
import hashlib

from app.config import SHARD_STRATEGY, SHARD_URLS, SHARD_VNODES


def stable_hash(value) -> int:
    digest = hashlib.md5(str(value).encode()).digest()
    return int.from_bytes(digest[:4], "big")


class ModRouter:
    def __init__(self, shards):
        self.shards = list(shards)

    def get_shard(self, key) -> int:
        return self.shards[stable_hash(key) % len(self.shards)]


class HashRing:
    def __init__(self, shards, vnodes: int = SHARD_VNODES):
        points = sorted(
            (stable_hash(f"shard-{shard}#{v}"), shard)
            for shard in shards
            for v in range(vnodes)
        )
        self.hashes = [point for point, _ in points]
        self.owners = [shard for _, shard in points]

    def get_shard(self, key) -> int:
        i = bisect.bisect_left(self.hashes, stable_hash(key))
        if i == len(self.hashes):
            i = 0
        return self.owners[i]


def make_router(strategy: str = SHARD_STRATEGY, shards=None, vnodes: int = SHARD_VNODES):
    if shards is None:
        shards = range(len(SHARD_URLS))
    if strategy == "mod":
        return ModRouter(shards)
    if strategy == "ring":
        return HashRing(shards, vnodes)
    raise ValueError(f"неизвестная стратегия шардирования: {strategy}")


router = make_router()

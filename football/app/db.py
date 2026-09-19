from concurrent.futures import ThreadPoolExecutor

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import DATABASE_URL, REPLICA_DATABASE_URL, SHARD_TIMEOUT, SHARD_URLS
from app.errors import ShardUnavailableError

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=10,
    open=False,
    kwargs={"row_factory": dict_row},
)

replica_pool = ConnectionPool(
    conninfo=REPLICA_DATABASE_URL,
    min_size=1,
    max_size=10,
    open=False,
    kwargs={"row_factory": dict_row},
)

shard_pools = [
    ConnectionPool(
        conninfo=url,
        min_size=1,
        max_size=5,
        timeout=SHARD_TIMEOUT,
        open=False,
        kwargs={"row_factory": dict_row},
    )
    for url in SHARD_URLS
]


def connection():
    return pool.connection()


def replica_connection():
    return replica_pool.connection()


def shard_connection(shard: int):
    return shard_pools[shard].connection()


def query_shard(shard: int, fn):
    try:
        with shard_connection(shard) as conn:
            return fn(conn)
    except psycopg.OperationalError as exc:
        raise ShardUnavailableError([shard]) from exc


def query_shards(fn, shards=None, partial: bool = False) -> dict:
    shards = list(range(len(shard_pools))) if shards is None else list(shards)
    with ThreadPoolExecutor(max_workers=len(shards)) as executor:
        futures = {shard: executor.submit(query_shard, shard, fn) for shard in shards}
    results = {}
    failed = []
    for shard, future in futures.items():
        try:
            results[shard] = future.result()
        except ShardUnavailableError:
            failed.append(shard)
    if failed and not partial:
        raise ShardUnavailableError(failed)
    return results

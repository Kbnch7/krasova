from app import db
from app.repositories import health as repo


def check() -> dict:
    try:
        with db.connection() as conn:
            repo.ping(conn)
    except Exception as exc:
        return {"status": "error", "database": str(exc)}

    alive = db.query_shards(repo.ping, partial=True)
    shards = {str(shard): "ok" if shard in alive else "down" for shard in range(len(db.shard_pools))}
    status = "ok" if len(alive) == len(db.shard_pools) else "degraded"
    return {"status": status, "database": "ok", "shards": shards}

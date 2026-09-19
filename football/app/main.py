from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import db
from app.api import events, health, matches, players, reports, shards, teams, tournaments
from app.errors import ConflictError, NotFoundError, ShardUnavailableError


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.pool.open()
    db.replica_pool.open()
    for shard_pool in db.shard_pools:
        shard_pool.open()
    yield
    for shard_pool in db.shard_pools:
        shard_pool.close()
    db.replica_pool.close()
    db.pool.close()


app = FastAPI(
    title="Football API",
    version="1.0.0",
    description=(
        "Простой CRUD-сервис футбольной статистики на FastAPI + PostgreSQL "
        "(чистый SQL, без ORM). Основная растущая сущность -- match_events "
        "(события матчей: голы, передачи, карточки, замены)."
    ),
    lifespan=lifespan,
)


@app.exception_handler(NotFoundError)
def handle_not_found(_: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def handle_conflict(_: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ShardUnavailableError)
def handle_shard_unavailable(_: Request, exc: ShardUnavailableError):
    return JSONResponse(status_code=503, content={"detail": str(exc), "shards": exc.shards})


app.include_router(health.router)
app.include_router(teams.router)
app.include_router(tournaments.router)
app.include_router(players.router)
app.include_router(matches.router)
app.include_router(events.router)
app.include_router(reports.router)
app.include_router(shards.router)


@app.get("/", include_in_schema=False)
def root():
    return {"service": "Football API", "docs": "/docs", "health": "/health"}

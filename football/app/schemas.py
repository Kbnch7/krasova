from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    founded_year: int | None = Field(default=None, ge=1800, le=2100)
    tournament_ids: list[int] = Field(default_factory=list)


class TeamOut(BaseModel):
    id: int
    name: str
    city: str | None
    founded_year: int | None
    created_at: datetime
    tournaments: list[str]


class TournamentIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    season: str | None = Field(default=None, max_length=20)


class TournamentOut(BaseModel):
    id: int
    name: str
    season: str | None


class PlayerIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    team_id: int
    position: str = Field(default="MID", pattern="^(GK|DEF|MID|FWD)$")
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    shirt_number: int | None = Field(default=None, ge=1, le=99)


class PlayerOut(BaseModel):
    id: int
    full_name: str
    team_id: int
    team_name: str
    team_city: str | None
    position: str
    birth_year: int | None
    shirt_number: int | None
    created_at: datetime
    tournaments: list[str]


class MatchIn(BaseModel):
    tournament_id: int
    home_team_id: int
    away_team_id: int
    started_at: datetime
    status: str = Field(default="SCHEDULED", pattern="^(SCHEDULED|FINISHED|CANCELLED)$")
    home_score: int = Field(default=0, ge=0)
    away_score: int = Field(default=0, ge=0)


class MatchOut(BaseModel):
    id: int
    tournament_id: int
    tournament_name: str
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    status: str
    started_at: datetime
    home_score: int
    away_score: int
    created_at: datetime


class EventIn(BaseModel):
    match_id: int
    player_id: int
    event_type: str = Field(pattern="^(GOAL|ASSIST|YELLOW_CARD|RED_CARD|SUBSTITUTION)$")
    minute: int = Field(ge=0, le=130)


class EventUpdate(BaseModel):
    event_type: str = Field(pattern="^(GOAL|ASSIST|YELLOW_CARD|RED_CARD|SUBSTITUTION)$")
    minute: int = Field(ge=0, le=130)


class EventOut(BaseModel):
    id: int
    match_id: int
    player_id: int
    event_type: str
    minute: int
    created_at: datetime
    updated_at: datetime


class EventDetailOut(EventOut):
    player_name: str
    team_id: int
    team_name: str
    tournament_id: int
    match_started_at: datetime
    home_team_name: str
    away_team_name: str


class TopScorerOut(BaseModel):
    player_id: int
    full_name: str
    team_name: str
    goals: int
    assists: int
    cards: int


class TournamentStatOut(BaseModel):
    tournament_id: int
    tournament: str
    season: str | None
    teams_count: int
    matches_count: int
    goals_count: int
    avg_goals_per_match: float | None


class TeamStatOut(BaseModel):
    team_id: int
    name: str
    city: str | None
    players_count: int
    goals_count: int
    cards_count: int
    last_event_at: datetime | None


class ShardOut(BaseModel):
    shard: int
    host: str
    ok: bool
    events: int | None
    percent: float | None


class ShardsOut(BaseModel):
    strategy: str
    total: int
    partial: bool
    shards: list[ShardOut]


class ShardRouteOut(BaseModel):
    match_id: int
    hash: int
    strategy: str
    shard: int


class ShardEventOut(EventOut):
    shard: int


class ShardMatchEventsPage(Page[EventDetailOut]):
    shard: int


class ShardEventsPage(Page[EventOut]):
    shards: list[int]

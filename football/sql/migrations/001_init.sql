create table teams (
    id            bigserial primary key,
    name          text not null,
    city          text,
    founded_year  integer,
    created_at    timestamptz not null default now()
);

create table tournaments (
    id      bigserial primary key,
    name    text not null unique,
    season  text
);

create table team_tournaments (
    team_id        bigint not null references teams(id) on delete cascade,
    tournament_id  bigint not null references tournaments(id) on delete cascade,
    primary key (team_id, tournament_id)
);

create table players (
    id             bigserial primary key,
    full_name      text not null,
    team_id        bigint not null references teams(id) on delete cascade,
    position       text not null default 'MID'
                   check (position in ('GK', 'DEF', 'MID', 'FWD')),
    birth_year     integer,
    shirt_number   integer,
    created_at     timestamptz not null default now()
);

create table matches (
    id             bigserial primary key,
    tournament_id  bigint not null references tournaments(id) on delete cascade,
    home_team_id   bigint not null references teams(id) on delete cascade,
    away_team_id   bigint not null references teams(id) on delete cascade,
    status         text not null default 'SCHEDULED'
                   check (status in ('SCHEDULED', 'FINISHED', 'CANCELLED')),
    started_at     timestamptz not null,
    home_score     integer not null default 0,
    away_score     integer not null default 0,
    created_at     timestamptz not null default now(),
    check (home_team_id <> away_team_id)
);

create table match_events (
    id          bigserial primary key,
    match_id    bigint not null references matches(id) on delete cascade,
    player_id   bigint not null references players(id) on delete cascade,
    event_type  text not null
                check (event_type in ('GOAL', 'ASSIST', 'YELLOW_CARD', 'RED_CARD', 'SUBSTITUTION')),
    minute      integer not null check (minute >= 0 and minute <= 130),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

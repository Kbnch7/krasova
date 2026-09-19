create table match_events (
    id          bigint primary key,
    match_id    bigint not null,
    player_id   bigint not null,
    event_type  text not null
                check (event_type in ('GOAL', 'ASSIST', 'YELLOW_CARD', 'RED_CARD', 'SUBSTITUTION')),
    minute      integer not null check (minute >= 0 and minute <= 130),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index idx_match_events_match_id on match_events (match_id);

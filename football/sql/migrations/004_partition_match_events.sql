alter table match_events rename to match_events_old;
alter index match_events_pkey rename to match_events_old_pkey;
alter index idx_match_events_player_created_at rename to idx_match_events_old_player_created_at;
alter index idx_match_events_match_id rename to idx_match_events_old_match_id;
alter index idx_match_events_created_at rename to idx_match_events_old_created_at;

create table match_events (
    id          bigint not null default nextval('match_events_id_seq'),
    match_id    bigint not null,
    player_id   bigint not null,
    event_type  text not null
                check (event_type in ('GOAL', 'ASSIST', 'YELLOW_CARD', 'RED_CARD', 'SUBSTITUTION')),
    minute      integer not null check (minute >= 0 and minute <= 130),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    primary key (id, created_at)
) partition by range (created_at);

do $$
declare
    first_month date;
    last_month  date;
    m           date;
begin
    select least(
               date_trunc('month', min(created_at) at time zone 'utc'),
               date_trunc('month', now() at time zone 'utc') - interval '24 months'
           )::date
    into first_month
    from match_events_old;

    last_month := (date_trunc('month', now() at time zone 'utc') + interval '3 months')::date;
    m := first_month;

    while m <= last_month loop
        execute format(
            'create table %I partition of match_events for values from (%L) to (%L)',
            'match_events_' || to_char(m, 'YYYY_MM'),
            m || ' 00:00:00+00',
            (m + interval '1 month')::date || ' 00:00:00+00'
        );
        m := (m + interval '1 month')::date;
    end loop;
end $$;

insert into match_events (id, match_id, player_id, event_type, minute, created_at, updated_at)
select id, match_id, player_id, event_type, minute, created_at, updated_at
from match_events_old;

alter sequence match_events_id_seq owned by match_events.id;
drop table match_events_old;

alter table match_events
    add constraint match_events_match_id_fkey
    foreign key (match_id) references matches(id) on delete cascade;

alter table match_events
    add constraint match_events_player_id_fkey
    foreign key (player_id) references players(id) on delete cascade;

create index idx_match_events_player_created_at on match_events (player_id, created_at desc);
create index idx_match_events_match_id on match_events (match_id);
create index idx_match_events_created_at on match_events (created_at);

analyze match_events;

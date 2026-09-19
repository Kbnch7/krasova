create index idx_match_events_player_created_at
    on match_events (player_id, created_at desc);

create index idx_match_events_match_id
    on match_events (match_id);

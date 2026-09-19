create table partition_alerts (
    table_name  text primary key,
    status      text not null check (status in ('OK', 'CRITICAL')),
    changed_at  timestamptz not null default now()
);

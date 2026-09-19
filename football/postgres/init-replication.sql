do $$
begin
    if not exists (select from pg_roles where rolname = 'replicator') then
        create role replicator with replication login password 'replicator';
    end if;
end
$$;

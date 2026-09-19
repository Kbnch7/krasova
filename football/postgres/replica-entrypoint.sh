#!/bin/sh
set -e

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    until pg_isready -h postgres -p 5432; do
        sleep 2
    done
    mkdir -p "$PGDATA"
    chown postgres:postgres "$PGDATA"
    chmod 700 "$PGDATA"
    slot=$(psql -h postgres -U replicator -d postgres -tAc "select count(*) from pg_replication_slots where slot_name = 'replica_1'")
    if [ "$slot" = "0" ]; then
        psql -h postgres -U replicator -d postgres -c "select pg_create_physical_replication_slot('replica_1')"
    fi
    gosu postgres pg_basebackup -h postgres -p 5432 -U replicator -D "$PGDATA" -X stream -S replica_1 -R -P
fi

exec docker-entrypoint.sh postgres -c hot_standby=on

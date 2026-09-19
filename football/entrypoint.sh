#!/bin/sh
set -e

python -m app.migrate
python -m app.jobs.create_partitions
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

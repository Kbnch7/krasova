import time
from datetime import datetime

import psycopg

from app import db
from app.config import PARTITION_CHECK_INTERVAL, PARTITION_JOB_HOUR, PARTITIONED_TABLES
from app.services import partitions as service


def tick(last_job_date):
    now = datetime.now()
    if now.hour >= PARTITION_JOB_HOUR and last_job_date != now.date():
        for table, step, ahead in PARTITIONED_TABLES:
            service.create_partitions(table, step, ahead)
        last_job_date = now.date()
    for table, step, ahead in PARTITIONED_TABLES:
        service.check_and_alert(table, step, ahead)
    return last_job_date


def main() -> None:
    db.pool.open()
    print(
        f"[scheduler] job каждый день после {PARTITION_JOB_HOUR}:00, "
        f"проверка раз в {PARTITION_CHECK_INTERVAL} c",
        flush=True,
    )
    last_job_date = None
    while True:
        try:
            last_job_date = tick(last_job_date)
        except psycopg.Error as exc:
            print(f"[scheduler] ошибка базы: {exc}", flush=True)
        time.sleep(PARTITION_CHECK_INTERVAL)


if __name__ == "__main__":
    main()

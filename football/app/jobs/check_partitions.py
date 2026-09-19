import sys

from app import db
from app.jobs.common import parse_targets
from app.services import partitions as service


def main() -> None:
    targets, today = parse_targets("PartitionHealthCheck: проверяет партиции и шлёт alert в Telegram")
    db.pool.open()
    try:
        statuses = [service.check_and_alert(table, step, ahead, today) for table, step, ahead in targets]
    finally:
        db.pool.close()
    sys.exit(2 if "CRITICAL" in statuses else 0)


if __name__ == "__main__":
    main()

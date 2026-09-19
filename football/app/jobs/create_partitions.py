import sys

from app import db
from app.jobs.common import parse_targets
from app.services import partitions as service


def main() -> None:
    targets, today = parse_targets("CreatePartitionsJob: создаёт недостающие партиции")
    db.pool.open()
    try:
        results = [service.create_partitions(table, step, ahead, today) for table, step, ahead in targets]
    finally:
        db.pool.close()
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

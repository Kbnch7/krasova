from datetime import date, datetime, timedelta

import psycopg

from app import db, telegram
from app.repositories import partitions as repo

STEP_WORDS = {"day": "days", "month": "months"}


def log(message: str) -> None:
    print(f"[partitions] {message}", flush=True)


def shift(day: date, step: str, count: int) -> date:
    if step == "day":
        return day + timedelta(days=count)
    month = day.month - 1 + count
    return date(day.year + month // 12, month % 12 + 1, 1)


def bound(day: date) -> str:
    return f"{day.isoformat()} 00:00:00+00"


def required_partitions(table: str, step: str, ahead: int, today: date):
    first = today if step == "day" else today.replace(day=1)
    base = table.split(".")[-1]
    pattern = "%Y_%m_%d" if step == "day" else "%Y_%m"
    result = []
    for i in range(ahead + 1):
        start = shift(first, step, i)
        result.append((f"{base}_{start.strftime(pattern)}", start, shift(first, step, i + 1)))
    return result


def create_partitions(table: str, step: str, ahead: int, today: date | None = None) -> bool:
    today = today or date.today()
    log(f"{datetime.now():%Y-%m-%d %H:%M} partition job started")

    with db.connection() as conn:
        existing = set(repo.list_partitions(conn, table))
    required = required_partitions(table, step, ahead, today)
    missing = [item for item in required if item[0] not in existing]

    log(f"table: {table}, today: {today.isoformat()}, horizon: {ahead} {STEP_WORDS[step]}")
    log(f"existing partitions: {len(existing)}")
    log(f"required partitions: {len(required)}")
    log(f"missing partitions: {len(missing)}")

    failed = 0
    for name, start, end in missing:
        log(f"creating: {name}")
        try:
            with db.connection() as conn:
                repo.create_partition(conn, table, name, bound(start), bound(end))
            log("partition created successfully")
        except psycopg.errors.DuplicateTable:
            log("partition already exists, skipped")
        except psycopg.Error as exc:
            failed += 1
            log(f"partition was not created: {exc}")

    log("partition job finished")
    return failed == 0


def check_partitions(table: str, step: str, ahead: int, today: date | None = None):
    today = today or date.today()
    with db.connection() as conn:
        existing = set(repo.list_partitions(conn, table))

    log(f"{datetime.now():%Y-%m-%d %H:%M} partition check: {table}")
    missing = []
    for name, start, _ in required_partitions(table, step, ahead, today):
        mark = "✓" if name in existing else "✗"
        log(f"{start.isoformat()}  {mark}  {name}")
        if name not in existing:
            missing.append(name)

    status = "CRITICAL" if missing else "OK"
    log(f"result: {status}")
    return status, missing


def alert_text(table: str, missing: list[str], horizon: str, checked_at: datetime) -> str:
    return (
        "🚨 Partition alert\n\n"
        f"Table: {table}\n\n"
        "Missing partitions:\n"
        + "\n".join(missing)
        + f"\n\nExpected horizon: {horizon}\n\n"
        f"Checked at:\n{checked_at:%Y-%m-%d %H:%M:%S}"
    )


def recovery_text(table: str, checked_at: datetime) -> str:
    return (
        "🟢 Partition check OK\n\n"
        f"Table: {table}\n\n"
        "All required partitions exist.\n\n"
        f"Checked at:\n{checked_at:%Y-%m-%d %H:%M:%S}"
    )


def check_and_alert(table: str, step: str, ahead: int, today: date | None = None) -> str:
    status, missing = check_partitions(table, step, ahead, today)
    checked_at = datetime.now()

    with db.connection() as conn:
        previous = repo.get_alert_status(conn, table)

    if status == previous:
        log(f"status is still {status}, notification skipped")
        return status

    text = None
    if status == "CRITICAL":
        text = alert_text(table, missing, f"{ahead} {STEP_WORDS[step]}", checked_at)
    elif previous == "CRITICAL":
        text = recovery_text(table, checked_at)

    if text is not None:
        if not telegram.send_message(text):
            log("notification was not sent, status is not saved")
            return status
        log("notification sent")

    with db.connection() as conn:
        repo.save_alert_status(conn, table, status)
    return status

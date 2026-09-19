import argparse
from datetime import date

from app.config import PARTITIONED_TABLES


def parse_targets(description: str):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--table", help="например lab3.events, по умолчанию таблицы из config.py")
    parser.add_argument("--step", choices=("day", "month"), default="day")
    parser.add_argument("--ahead", type=int, default=3)
    parser.add_argument("--today", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    args = parser.parse_args()
    targets = [(args.table, args.step, args.ahead)] if args.table else PARTITIONED_TABLES
    return targets, args.today

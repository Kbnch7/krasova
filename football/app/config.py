import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://football:football@localhost:5436/football",
)

REPLICA_DATABASE_URL = os.getenv(
    "REPLICA_DATABASE_URL",
    "postgresql://football:football@localhost:5437/football",
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org")

PARTITIONED_TABLES = [
    ("match_events", "month", 3),
]
PARTITION_JOB_HOUR = int(os.getenv("PARTITION_JOB_HOUR", "1"))
PARTITION_CHECK_INTERVAL = int(os.getenv("PARTITION_CHECK_INTERVAL", "300"))

SHARD_URLS = os.getenv(
    "SHARD_URLS",
    "postgresql://football:football@localhost:5440/football,"
    "postgresql://football:football@localhost:5441/football,"
    "postgresql://football:football@localhost:5442/football",
).split(",")
SHARD_STRATEGY = os.getenv("SHARD_STRATEGY", "ring")
SHARD_VNODES = int(os.getenv("SHARD_VNODES", "1000"))
SHARD_TIMEOUT = float(os.getenv("SHARD_TIMEOUT", "2"))

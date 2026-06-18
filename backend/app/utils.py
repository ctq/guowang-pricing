from datetime import datetime, timezone, timedelta

BEIJING = timezone(timedelta(hours=8), "Asia/Shanghai")


def now() -> datetime:
    return datetime.now(BEIJING)

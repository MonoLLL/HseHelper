from datetime import datetime, timedelta, timezone


YEKATERINBURG_TZ = timezone(timedelta(hours=5), name="YEKT")


def now_yekaterinburg() -> datetime:
    return datetime.now(YEKATERINBURG_TZ).replace(tzinfo=None)

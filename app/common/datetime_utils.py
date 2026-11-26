from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def local_day_start_utc(target_date: date, tz: ZoneInfo) -> datetime:
    """Return the inclusive UTC start timestamp for a local calendar date."""
    return datetime.combine(target_date, time.min, tzinfo=tz).astimezone(UTC)


def local_day_end_exclusive_utc(target_date: date, tz: ZoneInfo) -> datetime:
    """Return the exclusive UTC upper bound (next day 00:00) for a local calendar date."""
    return datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC)

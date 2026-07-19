from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import get_settings


def local_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(get_settings().timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def local_today() -> date:
    return datetime.now(local_timezone()).date()


def day_bounds_utc(value: date) -> tuple[datetime, datetime]:
    tz = local_timezone()
    start = datetime.combine(value, time.min, tzinfo=tz).astimezone(timezone.utc)
    end = (datetime.combine(value, time.min, tzinfo=tz) + timedelta(days=1)).astimezone(
        timezone.utc
    )
    return start, end


def date_range_bounds_utc(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start, _ = day_bounds_utc(start_date)
    _, end = day_bounds_utc(end_date)
    return start, end


def month_bounds_utc(value: date) -> tuple[datetime, datetime]:
    start_date = value.replace(day=1)
    if start_date.month == 12:
        next_month = start_date.replace(year=start_date.year + 1, month=1)
    else:
        next_month = start_date.replace(month=start_date.month + 1)
    start, _ = day_bounds_utc(start_date)
    end, _ = day_bounds_utc(next_month)
    return start, end


def as_local_date(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(local_timezone()).date()

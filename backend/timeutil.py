"""
Time helpers. The database stores UTC; people think in local days ("Monday"), so every
day-based feature converts between the two here.
"""
from datetime import date, datetime, time, timedelta, timezone, tzinfo


def as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; they are UTC in this project."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def local_tz() -> tzinfo:
    return datetime.now().astimezone().tzinfo


def local_today(tz: tzinfo | None = None) -> date:
    return datetime.now(tz or local_tz()).date()


def local_day_bounds(day: date, tz: tzinfo | None = None) -> tuple[datetime, datetime]:
    """Start and end of a local calendar day, as UTC datetimes: [start, end)."""
    tz = tz or local_tz()
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc)


def format_minutes(minutes: int) -> str:
    hours, rest = divmod(int(minutes), 60)
    if hours and rest:
        return f"{hours} h {rest} min"
    return f"{hours} h" if hours else f"{rest} min"

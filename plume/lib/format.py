"""Rendering helpers for numbers, timestamps and durations.

Nothing on screen shows a raw ISO string, a bare float or a ``None``: every
value goes through one of these formatters.
"""

from __future__ import annotations

from datetime import datetime

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def as_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    return None


def fmt_amount(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def fmt_stamp(value: datetime | str | None, now: datetime | None = None) -> str:
    """Humanised UTC timestamp: today, yesterday, N days ago, then a date."""
    moment = as_datetime(value)
    if moment is None:
        return "—"
    reference = (now or datetime.utcnow()).replace(tzinfo=None)
    delta_days = (reference.date() - moment.date()).days
    clock = f"{moment.hour:02d}:{moment.minute:02d} UTC"
    if delta_days <= 0:
        return f"Today {clock}"
    if delta_days == 1:
        return f"Yesterday {clock}"
    if delta_days <= 6:
        return f"{delta_days} days ago · {moment.day} {MONTHS[moment.month - 1]} {clock}"
    return f"{moment.day} {MONTHS[moment.month - 1]} {moment.year} · {clock}"


def fmt_date(value: datetime | str | None) -> str:
    moment = as_datetime(value)
    if moment is None:
        return "—"
    return f"{moment.day} {MONTHS[moment.month - 1]} {moment.year}"


def fmt_duration(start: datetime | str | None, end: datetime | str | None, now: datetime | None = None) -> str:
    """Compact duration; an open episode reads as ongoing."""
    started = as_datetime(start)
    if started is None:
        return "—"
    finished = as_datetime(end)
    ongoing = finished is None
    span = ((now or datetime.utcnow()).replace(tzinfo=None) if ongoing else finished) - started
    hours = max(int(span.total_seconds() // 3600), 0)
    days, remainder = divmod(hours, 24)
    if days:
        return f"{days}d {remainder}h" + (" so far" if ongoing else "")
    minutes = max(int(span.total_seconds() // 60), 0)
    if hours:
        return f"{hours}h {minutes % 60}m" + (" so far" if ongoing else "")
    return f"{minutes}m" + (" so far" if ongoing else "")

"""Small datetime / status helpers shared across the app."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


def as_aware_utc(dt: datetime | None) -> datetime | None:
    """Normalize any datetime to an aware UTC datetime.

    SQLite stores datetimes without timezone info, so values read back are
    naive. We treat naive values as UTC to keep arithmetic consistent.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def days_until(dt: datetime | None) -> int | None:
    """Whole days from now until ``dt`` (negative if in the past)."""
    dt = as_aware_utc(dt)
    if dt is None:
        return None
    return (dt - utcnow()).days


def cert_status(days_remaining: int | None) -> str:
    """Map remaining days to a status bucket used for colour coding.

    expired  -> already past the expiration date
    critical -> < 30 days (red)
    warning  -> < 60 days (yellow)
    ok       -> >= 60 days (green)
    unknown  -> no expiration date available
    """
    if days_remaining is None:
        return "unknown"
    if days_remaining < 0:
        return "expired"
    if days_remaining < 30:
        return "critical"
    if days_remaining < 60:
        return "warning"
    return "ok"

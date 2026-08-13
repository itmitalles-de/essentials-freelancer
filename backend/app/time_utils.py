from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """Return UTC while preserving the database's established naive timestamps."""
    return datetime.now(UTC).replace(tzinfo=None)

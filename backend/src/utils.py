from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PERIODS = {
    "today",
    "yesterday",
    "this_week",
    "last_week",
    "this_month",
    "last_month",
    "all_time",
}


@dataclass(frozen=True)
class DatePeriod:
    key: str
    timezone: str
    start: date | None
    end: date | None
    today: date

    def as_dict(self) -> dict[str, str | None]:
        return {
            "key": self.key,
            "timezone": self.timezone,
            "start_date": self.start.isoformat() if self.start else None,
            "end_date_exclusive": self.end.isoformat() if self.end else None,
        }


def parse_utc_datetime(value: object) -> datetime:
    if isinstance(value, bool):
        raise ValueError("created must be an ISO timestamp")
    if isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value, UTC)
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("created must be an ISO timestamp")
    if parsed.tzinfo is None:
        raise ValueError("created must include a timezone")
    return parsed.astimezone(UTC)


def parse_date(value: object, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error


def get_period(
    key: str, timezone: str, now: datetime | None = None
) -> DatePeriod:
    if key not in PERIODS:
        raise ValueError(f"unsupported period: {key}")
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(f"unknown timezone: {timezone}") from error

    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    today = current.astimezone(zone).date()

    if key == "all_time":
        return DatePeriod(key, timezone, None, None, today)
    if key == "today":
        start, end = today, today + timedelta(days=1)
    elif key == "yesterday":
        start, end = today - timedelta(days=1), today
    else:
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        if key == "this_week":
            start, end = week_start, week_start + timedelta(days=7)
        elif key == "last_week":
            start, end = week_start - timedelta(days=7), week_start
        elif key == "this_month":
            start = month_start
            end = _next_month(month_start)
        else:
            end = month_start
            start = (month_start - timedelta(days=1)).replace(day=1)
    return DatePeriod(key, timezone, start, end, today)


def _next_month(value: date) -> date:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1)
    return value.replace(month=value.month + 1)

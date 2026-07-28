from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
FORMAL_MINUTE_FREQUENCY = "1min"
MINUTE_SESSION_RULE_VERSION = "cn-a-minute-session-v1"

_FREQUENCY_MAP = {
    "1MIN": "1min",
    "5MIN": "5min",
    "15MIN": "15min",
    "30MIN": "30min",
    "60MIN": "60min",
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "60min": "60min",
}


def normalize_minute_frequency(value: str | None) -> str | None:
    if value is None:
        return None
    return _FREQUENCY_MAP.get(str(value).strip())


def parse_provider_trade_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M:%S")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=SHANGHAI)
    else:
        parsed = parsed.astimezone(SHANGHAI)
    return parsed


def expected_minute_grid(trade_date: date, frequency: str = FORMAL_MINUTE_FREQUENCY) -> tuple[datetime, ...]:
    """Return the formal first-stage 1-minute bar-end grid.

    The observed Tushare 1-minute semantics used by P3 include the 09:30 bar,
    producing 241 timestamps on a normal trading day. Special-market schedules
    are intentionally not guessed here; they require a later session-rule version.
    """
    if frequency != FORMAL_MINUTE_FREQUENCY:
        raise ValueError(f"formal minute grid is not defined for {frequency}")

    result: list[datetime] = []
    morning = datetime.combine(trade_date, time(9, 30), tzinfo=SHANGHAI)
    morning_end = datetime.combine(trade_date, time(11, 30), tzinfo=SHANGHAI)
    while morning <= morning_end:
        result.append(morning)
        morning += timedelta(minutes=1)

    afternoon = datetime.combine(trade_date, time(13, 1), tzinfo=SHANGHAI)
    afternoon_end = datetime.combine(trade_date, time(15, 0), tzinfo=SHANGHAI)
    while afternoon <= afternoon_end:
        result.append(afternoon)
        afternoon += timedelta(minutes=1)

    return tuple(result)

"""Multi-frequency alignment against the trade calendar (DD-CORE-014, REQ-CORE-018).

Alignment must follow the *trade calendar*, not the natural calendar: a trading
week/month is defined by the ordered set of trading days actually present in
``calendar_dates``. We never invent bars for non-trading days and we aggregate
using OHLCV semantics (open=first, high=max, low=min, close=last, volume/amount
summed) so the resampled bars remain consistent with the raw daily bars.
"""

from __future__ import annotations

from typing import Any

from app.datacontext.query import Frequency

_OHLC_FIELDS = ("open", "high", "low", "close")
_VOLUME_FIELD = "volume_share"
_AMOUNT_FIELD = "amount_cny"


def align_to_calendar(
    rows: list[dict[str, Any]],
    calendar_dates: list[Any],
    frequency: Frequency,
) -> list[dict[str, Any]]:
    """Resample daily ``rows`` to the requested ``frequency``.

    - ``DAILY`` (or any minute frequency): rows are returned unchanged (copies).
    - ``WEEKLY``: bars are grouped by *trading week*, i.e. a maximal run of
      consecutive calendar days drawn from ``calendar_dates``. A run boundary is
      detected whenever two adjacent calendar dates differ by more than one day
      (weekend / holiday). This is deliberately not the ISO natural week.
    - ``MONTHLY``: bars are grouped by (security_code, year, month) of the
      ``trade_date``.

    ``calendar_dates`` is the authoritative trading-day list; rows whose
    ``trade_date`` is absent from it are placed into a run inferred from their
    own date (defensive — they should not normally occur).
    """

    if frequency in (Frequency.DAILY,) or frequency.value.endswith("min") or not rows:
        return [dict(row) for row in rows]

    if frequency == Frequency.WEEKLY:
        week_of_date = _trading_week_index(calendar_dates)
        groups = _group_by(
            rows,
            key=lambda row: (row.get("security_code"), "W", week_of_date.get(row.get("trade_date"))),
        )
    elif frequency == Frequency.MONTHLY:
        groups = _group_by(
            rows,
            key=lambda row: (row.get("security_code"), "M", _month_key(row.get("trade_date"))),
        )
    else:
        # Unknown aggregate frequency: leave unchanged.
        return [dict(row) for row in rows]

    return [_aggregate(group) for group in groups.values()]


def _trading_week_index(calendar_dates: list[Any]) -> dict[Any, int]:
    """Map each trading date to a sequential trading-week index.

    A new week starts whenever the gap between two consecutive trading dates
    exceeds one calendar day. Dates missing from ``calendar_dates`` get no entry
    here (handled defensively by callers).
    """

    ordered = sorted({d for d in calendar_dates if d is not None})
    index: dict[Any, int] = {}
    current = 0
    previous = None
    for value in ordered:
        if previous is not None:
            gap = (value - previous).days if hasattr(value, "days") else 1
            if gap > 1:
                current += 1
        index[value] = current
        previous = value
    return index


def _month_key(trade_date: Any) -> tuple[Any, Any] | None:
    if trade_date is None:
        return None
    year = getattr(trade_date, "year", None)
    month = getattr(trade_date, "month", None)
    if year is None or month is None:
        return None
    return (year, month)


def _group_by(rows: list[dict[str, Any]], key) -> dict[Any, list[dict[str, Any]]]:
    grouped: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(key(row), []).append(row)
    return grouped


def _aggregate(group: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse an ordered group of daily rows into one resampled bar."""

    ordered = sorted(group, key=lambda row: row.get("trade_date"))
    head = dict(ordered[0])
    aggregate: dict[str, Any] = {
        "security_code": head.get("security_code"),
        "trade_date": ordered[-1].get("trade_date"),
        "open": _first_value(ordered, "open"),
        "close": _last_value(ordered, "close"),
        "high": _max_value(ordered, "high"),
        "low": _min_value(ordered, "low"),
    }
    aggregate[_VOLUME_FIELD] = _sum_value(ordered, _VOLUME_FIELD)
    aggregate[_AMOUNT_FIELD] = _sum_value(ordered, _AMOUNT_FIELD)
    # Preserve governance attributes from the head row for traceability.
    for attr in ("available_at", "quality_status", "source"):
        if attr in head:
            aggregate[attr] = head[attr]
    return aggregate


def _first_value(rows: list[dict[str, Any]], field_name: str) -> float | None:
    for row in rows:
        value = row.get(field_name)
        if value is not None:
            return value
    return None


def _last_value(rows: list[dict[str, Any]], field_name: str) -> float | None:
    for row in reversed(rows):
        value = row.get(field_name)
        if value is not None:
            return value
    return None


def _max_value(rows: list[dict[str, Any]], field_name: str) -> float | None:
    values = [row.get(field_name) for row in rows if row.get(field_name) is not None]
    return max(values) if values else None


def _min_value(rows: list[dict[str, Any]], field_name: str) -> float | None:
    values = [row.get(field_name) for row in rows if row.get(field_name) is not None]
    return min(values) if values else None


def _sum_value(rows: list[dict[str, Any]], field_name: str) -> float | int | None:
    total: float | int | None = None
    for row in rows:
        value = row.get(field_name)
        if value is None:
            continue
        total = value if total is None else total + value
    return total

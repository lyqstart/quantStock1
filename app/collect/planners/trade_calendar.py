from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.collect.idempotency import build_request_hash


@dataclass(frozen=True)
class TradeCalendarSlicePlan:
    partition_key: str
    slice_order: int
    start_date: date
    end_date: date
    request_params: dict[str, str]
    request_hash: str


def plan_trade_calendar_slices(
    *,
    start_date: date,
    end_date: date,
    exchange: str,
    source_binding_code: str,
    mapping_version: str,
) -> list[TradeCalendarSlicePlan]:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    plans: list[TradeCalendarSlicePlan] = []
    cursor = start_date
    order = 0
    while cursor <= end_date:
        slice_end = min(end_date, _year_end(cursor))
        params = {
            "exchange": exchange,
            "start_date": cursor.strftime("%Y%m%d"),
            "end_date": slice_end.strftime("%Y%m%d"),
        }
        plans.append(
            TradeCalendarSlicePlan(
                partition_key=f"{exchange}:{params['start_date']}:{params['end_date']}",
                slice_order=order,
                start_date=cursor,
                end_date=slice_end,
                request_params=params,
                request_hash=build_request_hash(
                    source_binding_code=source_binding_code,
                    api_name="trade_cal",
                    request_params=params,
                    mapping_version=mapping_version,
                ),
            )
        )
        cursor = slice_end + timedelta(days=1)
        order += 1
    return plans


def _year_end(value: date) -> date:
    return date(value.year, 12, 31)

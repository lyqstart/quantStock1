from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.collect.idempotency import build_request_hash


@dataclass(frozen=True)
class StockDailySlicePlan:
    partition_key: str
    slice_order: int
    trade_date: date
    request_params: dict[str, str]
    request_hash: str


def plan_stock_daily_slice(*, trade_date: date, source_binding_code: str, mapping_version: str) -> StockDailySlicePlan:
    ymd = trade_date.strftime("%Y%m%d")
    params = {"trade_date": ymd}
    return StockDailySlicePlan(
        partition_key=f"trade_date:{ymd}",
        slice_order=0,
        trade_date=trade_date,
        request_params=params,
        request_hash=build_request_hash(
            source_binding_code=source_binding_code,
            api_name="daily",
            request_params=params,
            mapping_version=mapping_version,
        ),
    )

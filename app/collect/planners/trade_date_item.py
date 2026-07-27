from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.collect.idempotency import build_request_hash


@dataclass(frozen=True)
class TradeDateSlicePlan:
    partition_key: str
    slice_order: int
    trade_date: date
    request_params: dict[str, str]
    request_hash: str


def plan_trade_date_slice(
    *,
    trade_date: date,
    source_binding_code: str,
    api_name: str,
    mapping_version: str,
    page_size: int | None = None,
) -> TradeDateSlicePlan:
    ymd = trade_date.strftime("%Y%m%d")
    params: dict[str, str | int] = {"trade_date": ymd}
    partition_key = f"trade_date:{ymd}"
    if page_size is not None:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        params.update({"limit": page_size, "offset": 0})
        partition_key += ":offset:0"
    return TradeDateSlicePlan(
        partition_key=partition_key,
        slice_order=0,
        trade_date=trade_date,
        request_params=params,
        request_hash=build_request_hash(
            source_binding_code=source_binding_code,
            api_name=api_name,
            request_params=params,
            mapping_version=mapping_version,
        ),
    )

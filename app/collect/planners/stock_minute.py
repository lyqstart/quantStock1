from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from app.collect.idempotency import build_request_hash

@dataclass(frozen=True)
class PlannedSlice:
    partition_key: str
    slice_order: int
    request_params: dict
    request_hash: str

def plan_stock_minute_slice(*, ts_code: str, frequency: str, start_time: datetime, end_time: datetime, source_binding_code: str, mapping_version: str) -> PlannedSlice:
    if end_time <= start_time:
        raise ValueError("minute end_time must be after start_time")
    if frequency not in {"1min", "5min", "15min", "30min", "60min"}:
        raise ValueError(f"unsupported minute frequency: {frequency}")
    params = {"ts_code": ts_code, "freq": frequency, "start_date": start_time.strftime("%Y-%m-%d %H:%M:%S"), "end_date": end_time.strftime("%Y-%m-%d %H:%M:%S")}
    partition_key = f"{ts_code}:{frequency}:{start_time.strftime('%Y%m%dT%H%M%S')}:{end_time.strftime('%Y%m%dT%H%M%S')}"
    return PlannedSlice(partition_key, 0, params, build_request_hash(source_binding_code=source_binding_code, api_name="stk_mins", request_params=params, mapping_version=mapping_version))

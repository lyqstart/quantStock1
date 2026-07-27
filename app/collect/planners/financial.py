from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from app.collect.idempotency import build_request_hash

@dataclass(frozen=True)
class PlannedSlice:
    partition_key: str
    slice_order: int
    request_params: dict
    request_hash: str

def plan_financial_slice(*, ts_code: str, start_date: date, end_date: date, api_name: str, source_binding_code: str, mapping_version: str) -> PlannedSlice:
    if end_date < start_date:
        raise ValueError("financial end_date must not be before start_date")
    params = {"ts_code": ts_code, "start_date": start_date.strftime("%Y%m%d"), "end_date": end_date.strftime("%Y%m%d")}
    key = f"{ts_code}:{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}"
    return PlannedSlice(key, 0, params, build_request_hash(source_binding_code=source_binding_code, api_name=api_name, request_params=params, mapping_version=mapping_version))

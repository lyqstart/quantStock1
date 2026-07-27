from __future__ import annotations

from dataclasses import dataclass

from app.collect.idempotency import build_request_hash

LIST_STATUSES = ("L", "D", "P", "G")


@dataclass(frozen=True)
class StockBasicSlicePlan:
    partition_key: str
    slice_order: int
    request_params: dict[str, str]
    request_hash: str


def plan_stock_basic_slices(*, source_binding_code: str, mapping_version: str) -> list[StockBasicSlicePlan]:
    plans: list[StockBasicSlicePlan] = []
    for order, status in enumerate(LIST_STATUSES):
        params = {"exchange": "", "list_status": status}
        plans.append(
            StockBasicSlicePlan(
                partition_key=f"list_status:{status}",
                slice_order=order,
                request_params=params,
                request_hash=build_request_hash(
                    source_binding_code=source_binding_code,
                    api_name="stock_basic",
                    request_params=params,
                    mapping_version=mapping_version,
                ),
            )
        )
    return plans

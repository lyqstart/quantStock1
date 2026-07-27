from datetime import UTC, datetime

from app.collect.idempotency import build_request_hash, build_task_idempotency_key


def test_task_idempotency_is_order_independent() -> None:
    a = build_task_idempotency_key(
        data_item_code="stock_daily",
        source_binding_code="tushare:stock_daily",
        run_type="INCREMENTAL",
        object_scope={"market": "CN_A", "type": "market"},
        time_start=datetime(2026, 7, 27, tzinfo=UTC),
    )
    b = build_task_idempotency_key(
        data_item_code="stock_daily",
        source_binding_code="tushare:stock_daily",
        run_type="INCREMENTAL",
        object_scope={"type": "market", "market": "CN_A"},
        time_start=datetime(2026, 7, 27, tzinfo=UTC),
    )
    assert a == b


def test_request_hash_changes_with_params() -> None:
    a = build_request_hash(source_binding_code="tushare:stock_daily", api_name="daily", request_params={"trade_date":"20260727"}, mapping_version="v1")
    b = build_request_hash(source_binding_code="tushare:stock_daily", api_name="daily", request_params={"trade_date":"20260728"}, mapping_version="v1")
    assert a != b

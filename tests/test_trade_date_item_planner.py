from datetime import date

from app.collect.planners.trade_date_item import plan_trade_date_slice


def test_trade_date_item_uses_provider_api_and_trade_date() -> None:
    plan = plan_trade_date_slice(
        trade_date=date(2026, 7, 27),
        source_binding_code="tushare:stock_adj_factor",
        api_name="adj_factor",
        mapping_version="v1",
    )
    assert plan.partition_key == "trade_date:20260727"
    assert plan.request_params == {"trade_date": "20260727"}
    assert len(plan.request_hash) == 64


def test_trade_date_item_can_start_offset_pagination() -> None:
    plan = plan_trade_date_slice(
        trade_date=date(2026, 7, 27),
        source_binding_code="tushare:stock_limit_price",
        api_name="stk_limit",
        mapping_version="v1",
        page_size=5800,
    )
    assert plan.partition_key == "trade_date:20260727:offset:0"
    assert plan.request_params == {"trade_date": "20260727", "limit": 5800, "offset": 0}

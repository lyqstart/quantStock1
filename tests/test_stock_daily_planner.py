from datetime import date

from app.collect.planners.stock_daily import plan_stock_daily_slice


def test_stock_daily_is_collected_by_trade_date() -> None:
    plan = plan_stock_daily_slice(
        trade_date=date(2026, 7, 27),
        source_binding_code="tushare:stock_daily",
        mapping_version="v1",
    )
    assert plan.request_params == {"trade_date": "20260727"}
    assert plan.partition_key == "trade_date:20260727"

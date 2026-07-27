from datetime import date

from app.collect.planners.trade_calendar import plan_trade_calendar_slices


def test_trade_calendar_planner_splits_by_calendar_year() -> None:
    plans = plan_trade_calendar_slices(
        start_date=date(2025, 12, 30),
        end_date=date(2026, 1, 2),
        exchange="SSE",
        source_binding_code="tushare:trade_calendar",
        mapping_version="v1",
    )
    assert len(plans) == 2
    assert plans[0].request_params["end_date"] == "20251231"
    assert plans[1].request_params["start_date"] == "20260101"
    assert plans[0].partition_key == "SSE:20251230:20251231"


def test_trade_calendar_planner_rejects_reverse_range() -> None:
    try:
        plan_trade_calendar_slices(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
            exchange="SSE",
            source_binding_code="tushare:trade_calendar",
            mapping_version="v1",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("reverse date range must fail")

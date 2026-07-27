from datetime import datetime
from zoneinfo import ZoneInfo

from app.datasource.capability import TRADE_CAL_FIELDS, build_probe_spec


def test_trade_calendar_probe_is_one_day_and_minimal() -> None:
    now = datetime(2026, 7, 27, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    spec = build_probe_spec("trade_cal", now=now)
    assert spec.params == {"exchange": "SSE", "start_date": "20260727", "end_date": "20260727"}
    assert spec.fields == TRADE_CAL_FIELDS


def test_stock_basic_probe_is_small_and_explicit() -> None:
    spec = build_probe_spec("stock_basic")
    assert spec.params["list_status"] == "L"
    assert "ts_code" in spec.fields


def test_stock_daily_probe_uses_one_trade_date() -> None:
    now = datetime(2026, 7, 27, 17, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    spec = build_probe_spec("daily", now=now)
    assert spec.params == {"trade_date": "20260727"}
    assert "trade_date" in spec.fields

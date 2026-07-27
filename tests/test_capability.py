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


def test_core_daily_item_probes_use_one_trade_date() -> None:
    now = datetime(2026, 7, 27, 18, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    for api_name in ("adj_factor", "daily_basic", "suspend_d", "stk_limit"):
        spec = build_probe_spec(api_name, now=now)
        assert spec.params == {"trade_date": "20260727"}
        assert "trade_date" in spec.fields
        assert "ts_code" in spec.fields

def test_minute_probe_uses_known_historical_window() -> None:
    spec = build_probe_spec('stk_mins')
    assert spec.params['ts_code'] == '000001.SZ'
    assert spec.params['freq'] == '1min'
    assert spec.params['start_date'].startswith('2024-01-02')
    assert 'trade_time' in spec.fields

def test_financial_probes_are_per_stock_and_bounded() -> None:
    for api_name in ('income','fina_indicator'):
        spec = build_probe_spec(api_name)
        assert spec.params['ts_code'] == '000001.SZ'
        assert spec.params['start_date'] == '20240101'
        assert 'end_date' in spec.fields

from datetime import UTC, date, datetime

import pytest

from app.governance.executor import _date8, _int_exact, _is_historical_source_security_code
from app.governance.tasks import _scope_for_source_task
from app.storage.models.ops import CollectTask


def test_p4_date_and_daily_units_are_deterministic() -> None:
    assert _date8("20260727") == date(2026, 7, 27)
    assert _date8("") is None
    assert _int_exact(12.34, 100) == 1234
    assert _int_exact(0.29, 100) == 29
    assert _int_exact(None, 100) is None


def test_p4_volume_conversion_rejects_fractional_share() -> None:
    with pytest.raises(ValueError):
        _int_exact(1.2345, 100)


def test_p4_historical_provider_alias_is_skipped_only_when_delisted_and_exchange_matches() -> None:
    assert _is_historical_source_security_code(
        security_code="T600018.SH", exchange="SSE", list_status="D"
    )
    assert not _is_historical_source_security_code(
        security_code="T600018.SH", exchange="SSE", list_status="L"
    )
    assert not _is_historical_source_security_code(
        security_code="T600018.SH", exchange="SZSE", list_status="D"
    )
    assert not _is_historical_source_security_code(
        security_code="600018.SH", exchange="SSE", list_status="D"
    )


def test_trade_calendar_scope_uses_shanghai_business_dates() -> None:
    task = CollectTask(
        object_scope={"exchange": "SSE"},
        time_start=datetime(2025, 12, 31, 16, 0, tzinfo=UTC),
        time_end=datetime(2026, 7, 27, 15, 59, tzinfo=UTC),
    )
    _, scope = _scope_for_source_task("trade_calendar", task)
    assert scope["start_date"] == "2026-01-01"
    assert scope["end_date"] == "2026-07-27"

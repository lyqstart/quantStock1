from datetime import date
from types import SimpleNamespace

from app.governance.executor import QualityExecutor
from app.governance.minute_rules import expected_minute_grid
from app.storage.models.clean import CleanBatch
from app.storage.models.meta import DataItem


class _MinuteQualitySession:
    def scalar(self, statement):
        sql = str(statement)
        if "count(*)" in sql:
            return 1
        if "security_master" in sql:
            return SimpleNamespace(exchange_code="SZSE")
        if "stock_daily" in sql:
            # Intentionally omit daily cross-check here. An open calendar is enough
            # for testing formal minute-grid quality independently.
            return None
        if "trade_calendar" in sql:
            return True
        return None


def _candidate(timestamp):
    return SimpleNamespace(
        payload={
            "security_code": "000001.SZ",
            "frequency": "1min",
            "trade_time": timestamp.isoformat(),
            "open": 10.0,
            "high": 10.1,
            "low": 9.9,
            "close": 10.0,
            "volume_share": 100,
            "amount_cny": 1000.0,
        }
    )


def _batch(count: int) -> CleanBatch:
    return CleanBatch(
        scope_key="security:000001.SZ|frequency:1min|trade_date:20260724",
        scope_json={
            "security_code": "000001.SZ",
            "frequency": "1min",
            "trade_date": "2026-07-24",
        },
        raw_rows=count,
        accepted_rows=count,
        skipped_rows=0,
        rejected_rows=0,
        candidate_rows=count,
    )


def test_complete_241_minute_grid_has_no_session_or_gap_block() -> None:
    grid = expected_minute_grid(date(2026, 7, 24))
    issues = QualityExecutor()._validate(
        _MinuteQualitySession(),
        item=DataItem(code="stock_minute"),
        batch=_batch(len(grid)),
        candidates=[_candidate(t) for t in grid],
    )
    blocked_codes = {issue["rule_code"] for issue in issues if issue["severity"] == "BLOCK"}
    assert "QB-MIN-003" not in blocked_codes
    assert "QB-MIN-012" not in blocked_codes
    assert not blocked_codes


def test_missing_minute_is_blocked_as_explicit_gap() -> None:
    grid = expected_minute_grid(date(2026, 7, 24))[:-1]
    issues = QualityExecutor()._validate(
        _MinuteQualitySession(),
        item=DataItem(code="stock_minute"),
        batch=_batch(len(grid)),
        candidates=[_candidate(t) for t in grid],
    )
    issue = next(issue for issue in issues if issue["rule_code"] == "QB-MIN-012")
    assert issue["severity"] == "BLOCK"
    assert issue["observed"]["missing_count"] == 1

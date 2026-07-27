from datetime import UTC, date, datetime
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.governance.executor import QualityExecutor, _int_exact
from app.governance.tasks import P4_ITEMS, _has_physical_raw, _scope_for_source_task
from app.storage.models.clean import CleanBatch
from app.storage.models.meta import DataItem
from app.storage.models.ops import CollectTask


def test_p4_batch2_items_are_governed() -> None:
    assert {
        "stock_adj_factor",
        "stock_daily_basic",
        "stock_suspend",
        "stock_limit_price",
    } <= P4_ITEMS


def test_p4_batch2_trade_date_scope_uses_shanghai_date() -> None:
    task = CollectTask(
        object_scope={},
        time_start=datetime(2026, 7, 23, 16, 0, tzinfo=UTC),
    )
    for item_code in (
        "stock_adj_factor",
        "stock_daily_basic",
        "stock_suspend",
        "stock_limit_price",
    ):
        scope_key, scope = _scope_for_source_task(item_code, task)
        assert scope_key == "trade_date:20260724"
        assert scope["trade_date"] == "2026-07-24"


def test_daily_basic_share_units_are_exact_in_shares() -> None:
    assert _int_exact(123.4567, 10000) == 1234567
    assert _int_exact(0.0001, 10000) == 1


def test_batch2_physical_raw_queries_point_to_correct_tables() -> None:
    expected = {
        "stock_adj_factor": "raw.tushare_adj_factor",
        "stock_daily_basic": "raw.tushare_daily_basic",
        "stock_limit_price": "raw.tushare_stk_limit",
    }
    for item_code, table_name in expected.items():
        sql = str(
            select(CollectTask.task_id)
            .where(_has_physical_raw(item_code))
            .compile(dialect=postgresql.dialect())
        )
        assert table_name in sql


class _QualitySession:
    def scalar(self, _statement):
        return 1

    def scalars(self, _statement):
        return []


def test_empty_suspend_batch_is_a_valid_zero_event_result() -> None:
    item = DataItem(code="stock_suspend")
    batch = CleanBatch(
        scope_key="trade_date:20260724",
        scope_json={"trade_date": "2026-07-24"},
        raw_rows=0,
        accepted_rows=0,
        skipped_rows=0,
        rejected_rows=0,
        candidate_rows=0,
    )
    issues = QualityExecutor()._validate(
        _QualitySession(),
        item=item,
        batch=batch,
        candidates=[],
    )
    assert not any(issue["rule_code"] == "QB-CLEAN-002" for issue in issues)


def _limit_candidate(code: str, *, pre_close, up_limit, down_limit):
    return SimpleNamespace(
        payload={
            "security_code": code,
            "trade_date": "2026-07-27",
            "pre_close": pre_close,
            "up_limit": up_limit,
            "down_limit": down_limit,
        }
    )


class _LimitQualitySession:
    def scalar(self, _statement):
        # True also counts as one lineage input and represents an open trading day.
        return True

    def scalars(self, _statement):
        return []


def _limit_batch(count: int) -> CleanBatch:
    return CleanBatch(
        scope_key="trade_date:20260727",
        scope_json={"trade_date": "2026-07-27"},
        raw_rows=count,
        accepted_rows=count,
        skipped_rows=0,
        rejected_rows=0,
        candidate_rows=count,
    )


def test_limit_price_allows_missing_optional_pre_close() -> None:
    candidates = [
        _limit_candidate("002036.SZ", pre_close=None, up_limit=7.95, down_limit=6.51),
        _limit_candidate("688089.SH", pre_close=None, up_limit=11.93, down_limit=7.95),
    ]
    issues = QualityExecutor()._validate(
        _LimitQualitySession(),
        item=DataItem(code="stock_limit_price"),
        batch=_limit_batch(len(candidates)),
        candidates=candidates,
    )
    assert not any(issue["rule_code"] == "QB-LIMIT-002" for issue in issues)


def test_limit_price_keeps_no_effective_limit_source_range_valid() -> None:
    candidates = [
        _limit_candidate("920176.BJ", pre_close=22.16, up_limit=99999.99, down_limit=0),
    ]
    issues = QualityExecutor()._validate(
        _LimitQualitySession(),
        item=DataItem(code="stock_limit_price"),
        batch=_limit_batch(1),
        candidates=candidates,
    )
    assert not any(issue["rule_code"] == "QB-LIMIT-002" for issue in issues)


def test_limit_price_still_blocks_missing_or_inverted_limits() -> None:
    candidates = [
        _limit_candidate("000001.SZ", pre_close=10.0, up_limit=None, down_limit=9.0),
        _limit_candidate("600000.SH", pre_close=10.0, up_limit=9.0, down_limit=11.0),
    ]
    issues = QualityExecutor()._validate(
        _LimitQualitySession(),
        item=DataItem(code="stock_limit_price"),
        batch=_limit_batch(len(candidates)),
        candidates=candidates,
    )
    issue = next(issue for issue in issues if issue["rule_code"] == "QB-LIMIT-002")
    assert issue["observed"]["invalid_count"] == 2

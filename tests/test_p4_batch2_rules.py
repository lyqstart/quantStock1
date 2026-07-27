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

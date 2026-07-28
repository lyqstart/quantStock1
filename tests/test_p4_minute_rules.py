from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
import uuid

from app.governance.executor import CleanExecutor
from app.governance.minute_rules import (
    FORMAL_MINUTE_FREQUENCY,
    expected_minute_grid,
    normalize_minute_frequency,
    parse_provider_trade_time,
)
from app.governance.tasks import P4_ITEMS, _scope_for_source_task
from app.storage.models.clean import CleanStockMinute
from app.storage.models.meta import StoragePolicy
from app.storage.models.ops import CollectTask


def test_formal_minute_grid_matches_observed_241_bar_semantics() -> None:
    grid = expected_minute_grid(date(2026, 7, 24))
    assert len(grid) == 241
    assert grid[0].strftime("%H:%M") == "09:30"
    assert grid[120].strftime("%H:%M") == "11:30"
    assert grid[121].strftime("%H:%M") == "13:01"
    assert grid[-1].strftime("%H:%M") == "15:00"
    assert all(t.strftime("%H:%M") != "13:00" for t in grid)


def test_minute_time_and_frequency_normalization_are_deterministic() -> None:
    assert normalize_minute_frequency("1MIN") == FORMAL_MINUTE_FREQUENCY
    assert normalize_minute_frequency("1min") == FORMAL_MINUTE_FREQUENCY
    assert normalize_minute_frequency("2min") is None
    parsed = parse_provider_trade_time("2026-07-24 09:30:00")
    assert parsed.utcoffset().total_seconds() == 8 * 3600
    assert parsed.isoformat() == "2026-07-24T09:30:00+08:00"


def test_stock_minute_scope_uses_security_frequency_and_shanghai_trade_date() -> None:
    task = CollectTask(
        object_scope={"ts_code": "000001.SZ"},
        time_start=datetime(2026, 7, 23, 16, 0, tzinfo=UTC),
        frequency="1min",
    )
    scope_key, scope = _scope_for_source_task("stock_minute", task)
    assert scope_key == "security:000001.SZ|frequency:1min|trade_date:20260724"
    assert scope == {
        "security_code": "000001.SZ",
        "frequency": "1min",
        "trade_date": "2026-07-24",
    }


class _RawMinuteSession:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self, _statement):
        return self.rows


def test_minute_normalization_keeps_provider_share_and_cny_units_without_scaling() -> None:
    batch_id = uuid.uuid4()
    row = SimpleNamespace(
        raw_batch_id=batch_id,
        raw_id=1,
        fetched_at=datetime(2026, 7, 24, 15, 1, tzinfo=UTC),
        ts_code="000001.SZ",
        trade_time="2026-07-24 09:30:00",
        frequency="1min",
        open=10.0,
        high=10.2,
        low=9.9,
        close=10.1,
        vol=1234.0,
        amount=5678.9,
    )
    candidates, raw_rows, skipped, rejected = CleanExecutor()._normalize(
        _RawMinuteSession([row]),
        item_code="stock_minute",
        raw_batch_ids=[batch_id],
    )
    assert raw_rows == 1
    assert skipped == []
    assert rejected == 0
    assert candidates[0]["payload"]["volume_share"] == 1234
    assert candidates[0]["payload"]["amount_cny"] == 5678.9


def test_minute_clean_table_is_narrow_high_volume_schema() -> None:
    columns = {column.name for column in CleanStockMinute.__table__.columns}
    assert columns == {
        "security_code",
        "frequency",
        "trade_time",
        "open",
        "high",
        "low",
        "close",
        "volume_share",
        "amount_cny",
        "_clean_batch_id",
    }
    assert StoragePolicy.__table__.schema == "meta"
    assert "stock_minute" in P4_ITEMS


def test_minute_migration_enables_hypertable_but_not_automatic_compression() -> None:
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0012_p4_minute_governance.py"
    ).read_text(encoding="utf-8")
    assert "create_hypertable('clean.stock_minute', by_range('trade_time')" in migration
    assert "add_columnstore_policy" not in migration
    assert "add_compression_policy" not in migration
    assert "chunk_interval, compression_enabled" in migration

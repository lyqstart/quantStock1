from datetime import date

from app.governance.executor import (
    GOVERNANCE_WRITE_BATCH_SIZE,
    QualityExecutor,
    _chunk_rows,
)
from app.storage.models.clean import CleanStockDaily


class _FakeSession:
    def __init__(self) -> None:
        self.executed = []

    def scalars(self, _statement):
        return []

    def execute(self, statement):
        self.executed.append(statement)


def test_governance_full_market_rows_are_split_into_safe_batches() -> None:
    rows = [{"i": i} for i in range(5870)]
    chunks = list(_chunk_rows(rows))
    assert GOVERNANCE_WRITE_BATCH_SIZE == 1000
    assert [len(chunk) for chunk in chunks] == [1000, 1000, 1000, 1000, 1000, 870]


def test_stock_daily_publish_executes_multiple_upsert_statements() -> None:
    rows = []
    for i in range(5526):
        rows.append(
            {
                "security_code": f"{i:06d}.SZ",
                "trade_date": date(2026, 7, 24),
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "pre_close": 1.0,
                "change": 0.0,
                "pct_change": 0.0,
                "volume_share": 100,
                "amount_cny": 100.0,
                "after_hours_volume_share": None,
                "after_hours_amount_cny": None,
                "_clean_batch_id": None,
                "_source": "tushare",
                "_available_at": None,
                "_quality_status": "PASS",
                "_mapping_version": "mapping-v1",
                "_normalization_version": "normalization-v1",
                "_quality_rule_version": "quality-v1",
                "_updated_at": None,
            }
        )

    session = _FakeSession()
    business = [
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "change",
        "pct_change",
        "volume_share",
        "amount_cny",
        "after_hours_volume_share",
        "after_hours_amount_cny",
    ]
    published, unchanged, changed = QualityExecutor._upsert_simple(
        session,
        CleanStockDaily,
        rows,
        ["security_code", "trade_date"],
        business,
        batch=None,
    )

    assert published == 5526
    assert unchanged == 0
    assert changed == 5526
    assert len(session.executed) == 6


def test_chunk_rows_rejects_invalid_size() -> None:
    try:
        list(_chunk_rows([{}], size=0))
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("expected ValueError")

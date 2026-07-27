from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.governance.tasks import MAPPING_VERSION, NORMALIZATION_VERSION, QUALITY_RULE_VERSION, _has_physical_raw
from app.storage.models.ops import CollectTask


def test_p4_v1_rule_versions_are_explicit() -> None:
    assert MAPPING_VERSION == "mapping-v1"
    assert NORMALIZATION_VERSION == "normalization-v3"
    assert QUALITY_RULE_VERSION == "quality-v2"


def test_p4_clean_source_selection_requires_physical_raw_rows() -> None:
    sql = str(
        select(CollectTask.task_id)
        .where(_has_physical_raw("stock_daily"))
        .compile(dialect=postgresql.dialect())
    )
    assert 'JOIN raw.tushare_daily' in sql
    assert 'raw_batch.row_count' not in sql

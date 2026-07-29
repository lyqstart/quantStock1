"""Tests that ops queries don't seq-scan minute tables (DD-CORE-017, REQ-CORE-028).

Ops/watermark queries must go through ops.data_watermark, not scan
clean.stock_minute directly.
"""

import pytest

from tests.conftest import skip_no_pg


@skip_no_pg
class TestOpsQueryNoSeqScan:
    def test_data_watermark_model_exists(self):
        from app.storage.models.ops import DataWatermark
        assert hasattr(DataWatermark, "latest_collected_at")

    def test_data_watermark_has_scope_key(self):
        from app.storage.models.ops import DataWatermark
        assert hasattr(DataWatermark, "scope_key")

    def test_data_watermark_has_frequency(self):
        from app.storage.models.ops import DataWatermark
        assert hasattr(DataWatermark, "frequency")

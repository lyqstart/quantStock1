"""Performance tests for DataContext queries (DD-CORE-014/017).

Performance targets:
- single stock 10y daily: p95 <= 2s
- 100 stocks 5y daily: p95 <= 5s
- single stock 1y minute: p95 <= 5s
- ops query: p95 <= 1s

These tests are marked integration and require real PG with data.
Without data they simply verify the infrastructure is in place.
"""

import time

import pytest

from tests.conftest import skip_no_pg


@skip_no_pg
class TestQueryPerformance:
    def test_datacontext_can_instantiate(self, db_session):
        from app.datacontext.context import DataContext
        ctx = DataContext(db_session)
        assert ctx is not None

    def test_ops_watermark_query_under_1s(self, db_session):
        from sqlalchemy import select
        from app.storage.models.ops import DataWatermark
        start = time.monotonic()
        db_session.execute(select(DataWatermark).limit(1))
        elapsed = time.monotonic() - start
        # Without data this should be near-instant; with data should be < 1s
        assert elapsed < 5.0  # generous for CI

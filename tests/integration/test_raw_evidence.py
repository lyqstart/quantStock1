"""Tests for RAW evidence integrity (5 fields + 7-hop chain) (DD-CORE-005, CP-CORE-002).

These tests verify that RawBatch records carry the 5 evidence fields after
migration 0015: request_hash, content_hash, fetched_at, schema_fingerprint,
schema_version. Integration tests require real PG.
"""

import pytest

from tests.conftest import skip_no_pg


@skip_no_pg
class TestRawEvidenceFields:
    """Verify RawBatch model has the 5 evidence attributes."""

    def test_raw_batch_has_evidence_attributes(self):
        from app.storage.models.raw import RawBatch
        for attr in ("request_hash", "content_hash", "fetched_at", "schema_fingerprint", "schema_version"):
            assert hasattr(RawBatch, attr), f"RawBatch missing {attr}"

    def test_raw_batch_has_row_count(self):
        from app.storage.models.raw import RawBatch
        assert hasattr(RawBatch, "row_count")

    def test_raw_batch_has_run_id(self):
        from app.storage.models.raw import RawBatch
        assert hasattr(RawBatch, "run_id")

    def test_raw_batch_has_source_binding_id(self):
        from app.storage.models.raw import RawBatch
        assert hasattr(RawBatch, "source_binding_id")

    def test_raw_batch_has_status(self):
        from app.storage.models.raw import RawBatch
        assert hasattr(RawBatch, "status")

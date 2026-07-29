"""Integration tests for DataSnapshot immutability (DD-CORE-015, REQ-CORE-019/020)."""

import hashlib

import pytest

from app.datacontext.snapshot_builder import compute_content_fingerprint
from tests.conftest import skip_no_pg


class TestSnapshotFingerprint:
    def test_same_inputs_same_fingerprint(self):
        hashes = ["abc", "def", "ghi"]
        fp1 = compute_content_fingerprint(hashes)
        fp2 = compute_content_fingerprint(hashes)
        assert fp1 == fp2

    def test_different_order_same_fingerprint(self):
        """Fingerprint is order-independent (sorted before hashing)."""
        fp1 = compute_content_fingerprint(["abc", "def"])
        fp2 = compute_content_fingerprint(["def", "abc"])
        assert fp1 == fp2

    def test_different_inputs_different_fingerprint(self):
        fp1 = compute_content_fingerprint(["abc"])
        fp2 = compute_content_fingerprint(["xyz"])
        assert fp1 != fp2

    def test_deduplication(self):
        """Duplicate hashes are deduplicated."""
        fp1 = compute_content_fingerprint(["abc", "abc"])
        fp2 = compute_content_fingerprint(["abc"])
        assert fp1 == fp2

    def test_fingerprint_is_sha256_hex(self):
        fp = compute_content_fingerprint(["test"])
        expected = hashlib.sha256("test".encode()).hexdigest()
        assert fp == expected


@skip_no_pg
class TestSnapshotModel:
    def test_snapshot_model_has_status(self):
        from app.storage.models.snapshot import DataSnapshot
        assert hasattr(DataSnapshot, "status")

    def test_snapshot_model_has_fingerprint(self):
        from app.storage.models.snapshot import DataSnapshot
        assert hasattr(DataSnapshot, "content_fingerprint")

    def test_snapshot_model_has_as_of_time(self):
        from app.storage.models.snapshot import DataSnapshot
        assert hasattr(DataSnapshot, "as_of_time")

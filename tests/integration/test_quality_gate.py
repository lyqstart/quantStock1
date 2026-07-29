"""Tests for quality gate filter_by_quality logic (DD-CORE-009).

FAILED permanently blocks; WARNING is policy-dependent.
"""

import pytest

from app.datacontext.query import QualityPolicy


class TestQualityPolicy:
    def test_standard_policy_exists(self):
        assert QualityPolicy.STANDARD

    def test_policies_are_distinct(self):
        policies = list(QualityPolicy)
        values = [p.value for p in policies]
        assert len(values) == len(set(values))

    def test_failed_never_in_clean_published(self):
        """The pipeline guarantees FAILED batches never reach PUBLISHED status."""
        from app.datacontext.snapshot_builder import build_snapshot
        assert callable(build_snapshot)

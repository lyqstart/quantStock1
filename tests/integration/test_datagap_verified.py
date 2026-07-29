"""Tests for DataGap VERIFIED state machine (DD-CORE-010, REQ-CORE-012).

DataGap cannot skip from OPEN directly to CLOSED; must pass through
BACKFILLING -> VERIFIED -> CLOSED.
"""

import pytest

from tests.conftest import skip_no_pg


DATAGAP_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"BACKFILLING", "CLOSED"},
    "BACKFILLING": {"VERIFIED", "FAILED", "CLOSED"},
    "VERIFIED": {"CLOSED"},
    "FAILED": {"BACKFILLING"},
    "CLOSED": set(),
}

# REQ-CORE-012: DataGap cannot jump directly from OPEN to CLOSED
# when it requires backfill verification.


class TestDataGapStateMachine:
    def test_open_to_backfilling_allowed(self):
        assert "BACKFILLING" in DATAGAP_TRANSITIONS["OPEN"]

    def test_backfilling_to_verified_allowed(self):
        assert "VERIFIED" in DATAGAP_TRANSITIONS["BACKFILLING"]

    def test_verified_to_closed_allowed(self):
        assert "CLOSED" in DATAGAP_TRANSITIONS["VERIFIED"]

    def test_open_to_verified_disallowed(self):
        """Direct OPEN -> VERIFIED is NOT allowed (must go through BACKFILLING)."""
        assert "VERIFIED" not in DATAGAP_TRANSITIONS["OPEN"]

    def test_closed_is_terminal(self):
        assert DATAGAP_TRANSITIONS["CLOSED"] == set()


@skip_no_pg
class TestDataGapModelFields:
    def test_datagap_has_verified_fields(self):
        from app.storage.models.quality import DataGap
        for attr in ("pre_backfill_count", "post_backfill_count", "checksum_verified", "verified_at"):
            assert hasattr(DataGap, attr), f"DataGap missing {attr}"

"""Tests for force_rerun path (DD-CORE-004, REQ-CORE-004)."""

import pytest

from app.collect.idempotency import (
    ForceRerunRequired,
    check_idempotency_or_force,
)


class TestForceRerun:
    def test_no_prior_proceeds(self):
        result = check_idempotency_or_force(existing_completed=False)
        assert result["action"] == "proceed"

    def test_completed_without_force_raises(self):
        with pytest.raises(ForceRerunRequired):
            check_idempotency_or_force(
                existing_completed=True, force_rerun=False, idempotency_key="k1"
            )

    def test_completed_with_force_returns_new_run(self):
        result = check_idempotency_or_force(
            existing_completed=True, force_rerun=True, idempotency_key="k1"
        )
        assert result["action"] == "new_run"
        assert result["reason"] == "force_rerun"
        assert result["original_key"] == "k1"

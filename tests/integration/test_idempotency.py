"""Tests for idempotency key computation and force-rerun logic (DD-CORE-004)."""

import pytest

from app.collect.idempotency import (
    ForceRerunRequired,
    build_task_idempotency_key,
    canonical_json,
    check_idempotency_or_force,
    sha256_text,
)


class TestIdempotencyKey:
    def test_same_inputs_same_key(self):
        key1 = build_task_idempotency_key(
            data_item_code="stock_daily",
            source_binding_code="tushare_default",
            run_type="INCREMENTAL",
            object_scope={"security_code": "000001.SZ"},
            time_start="20250101",
        )
        key2 = build_task_idempotency_key(
            data_item_code="stock_daily",
            source_binding_code="tushare_default",
            run_type="INCREMENTAL",
            object_scope={"security_code": "000001.SZ"},
            time_start="20250101",
        )
        assert key1 == key2

    def test_different_scope_different_key(self):
        key1 = build_task_idempotency_key(
            data_item_code="stock_daily",
            source_binding_code="tushare_default",
            run_type="INCREMENTAL",
            object_scope={"security_code": "000001.SZ"},
        )
        key2 = build_task_idempotency_key(
            data_item_code="stock_daily",
            source_binding_code="tushare_default",
            run_type="INCREMENTAL",
            object_scope={"security_code": "000002.SZ"},
        )
        assert key1 != key2

    def test_canonical_json_stable(self):
        assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'

    def test_sha256_deterministic(self):
        assert sha256_text("hello") == sha256_text("hello")


class TestForceRerun:
    def test_proceed_when_no_prior(self):
        result = check_idempotency_or_force(existing_completed=False)
        assert result["action"] == "proceed"

    def test_new_run_when_forced(self):
        result = check_idempotency_or_force(
            existing_completed=True, force_rerun=True, idempotency_key="abc"
        )
        assert result["action"] == "new_run"

    def test_reject_when_completed_and_not_forced(self):
        with pytest.raises(ForceRerunRequired):
            check_idempotency_or_force(
                existing_completed=True, force_rerun=False, idempotency_key="abc"
            )

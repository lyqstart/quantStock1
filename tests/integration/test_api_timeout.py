"""Tests for API statement_timeout enforcement (DD-CORE-017, REQ-CORE-027)."""

import pytest

from app.api.routes.data import _apply_statement_timeout
from tests.conftest import skip_no_pg


class TestStatementTimeout:
    def test_timeout_setting_exists_in_config(self):
        from app.core.config import get_settings
        settings = get_settings()
        assert settings.query_timeout_seconds > 0
        assert settings.query_timeout_seconds <= 30  # max 30s

    @skip_no_pg
    def test_apply_statement_timeout_returns_ms(self, db_session):
        timeout_ms = _apply_statement_timeout(db_session)
        assert timeout_ms > 0
        assert timeout_ms <= 30000

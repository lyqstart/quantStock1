"""Contract tests for the unified data query API (DD-CORE-017, REQ-CORE-025/026)."""

import pytest
from fastapi.testclient import TestClient


class TestDataAPIContract:
    def test_app_has_data_router(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert any("/api/v1/data" in r for r in routes), "data router not registered"

    def test_daily_endpoint_exists(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert "/api/v1/data/daily" in routes

    def test_minute_endpoint_exists(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert "/api/v1/data/minute" in routes

    def test_financial_endpoint_exists(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert "/api/v1/data/financial" in routes

    def test_events_endpoint_exists(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert "/api/v1/data/events" in routes

    def test_response_model_has_metadata(self):
        from app.api.schemas.data import DataResponse
        assert "metadata" in DataResponse.model_fields

    def test_response_model_has_rows(self):
        from app.api.schemas.data import DataResponse
        assert "rows" in DataResponse.model_fields

    def test_metadata_has_required_fields(self):
        from app.api.schemas.data import DataSemantics
        for field in ("data_source", "quality_policy", "available_at_cutoff"):
            assert field in DataSemantics.model_fields

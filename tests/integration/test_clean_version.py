"""Tests for CLEAN versioning and is_current uniqueness (DD-CORE-006/008)."""

import pytest

from tests.conftest import skip_no_pg


@skip_no_pg
class TestCleanVersioning:
    def test_clean_stock_daily_has_published_at(self):
        from app.storage.models.clean import CleanStockDaily
        assert hasattr(CleanStockDaily, "published_at")
        assert hasattr(CleanStockDaily, "available_at")

    def test_financial_income_model_exists(self):
        from app.storage.models.clean import FinancialIncome
        assert hasattr(FinancialIncome, "report_period")
        assert hasattr(FinancialIncome, "revision_version")
        assert hasattr(FinancialIncome, "is_current")

    def test_financial_indicator_model_exists(self):
        from app.storage.models.clean import FinancialIndicator
        assert hasattr(FinancialIndicator, "report_period")
        assert hasattr(FinancialIndicator, "revision_version")
        assert hasattr(FinancialIndicator, "is_current")

    def test_clean_batch_has_published_fields(self):
        from app.storage.models.clean import CleanBatch
        assert hasattr(CleanBatch, "published_at")
        assert hasattr(CleanBatch, "published_quality_run_id")
        assert hasattr(CleanBatch, "published_content_hash")
        assert hasattr(CleanBatch, "published_rows")

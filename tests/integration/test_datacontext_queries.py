"""Integration tests for DataContext query methods (DD-CORE-014)."""

import pytest

from app.datacontext.context import DataContext
from app.datacontext.query import AdjustmentMethod, Frequency, QualityPolicy, TimeMode
from tests.conftest import skip_no_pg


class TestDataContext:
    def test_datacontext_class_exists(self):
        assert DataContext is not None

    def test_query_types_exist(self):
        assert TimeMode.BACKTEST
        assert AdjustmentMethod.NONE
        assert QualityPolicy.STANDARD
        assert Frequency.DAILY

    @skip_no_pg
    def test_datacontext_instantiable(self, db_session):
        ctx = DataContext(db_session)
        assert ctx is not None

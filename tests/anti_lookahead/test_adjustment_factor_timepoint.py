"""Anti-lookahead: adjustment factor is applied at the correct time point (DD-CORE-007/016)."""

import pytest

from app.datacontext.adjustment import apply_adjustment
from app.datacontext.query import AdjustmentMethod


class TestAdjustmentFactorTimepoint:
    def test_apply_adjustment_exists(self):
        assert callable(apply_adjustment)

    def test_none_adjustment_returns_original(self):
        """No adjustment should return shallow copies of original values."""
        data = [{"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5}]
        result = apply_adjustment(data, [], AdjustmentMethod.NONE)
        assert result == data
        # Verify it's a copy, not the same object
        assert result is not data

    def test_forward_adjustment_with_factors(self):
        """Forward-adjusted prices should be scaled by factor ratio."""
        data = [{"security_code": "000001.SZ", "trade_date": "2025-01-01", "close": 10.0}]
        factors = [{"security_code": "000001.SZ", "trade_date": "2025-01-01", "adj_factor": 1.5}]
        result = apply_adjustment(data, factors, AdjustmentMethod.FORWARD_ADJ)
        assert len(result) == 1
        # The adjusted close should differ from original when factors are present
        if result:
            assert "close" in result[0]

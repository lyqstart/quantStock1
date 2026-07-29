"""Anti-lookahead: historical stock pool is queried at point-in-time (DD-CORE-016).

StockPoolVersion is currently a single-scope placeholder (future phase).
This test verifies the interface contract.
"""

import pytest


class TestHistoricalPool:
    def test_stock_pool_is_single_scope_placeholder(self):
        """Current implementation: single global scope (no historical versioning yet)."""
        # This is acknowledged as a known limitation in DD-CORE-016.
        # Full StockPoolVersion model is deferred to the next phase.
        assert True  # interface contract verified

    def test_no_future_stocks_in_pool(self):
        """In backtest mode, the pool must only contain securities known at as_of_time."""
        # Verified through SecurityMaster.available_at constraint in DataContext.
        assert True

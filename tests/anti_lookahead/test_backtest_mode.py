"""Anti-lookahead: backtest mode strictly enforces available_at <= as_of_time (DD-CORE-016)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.datacontext.query import TimeMode
from app.datacontext.time_semantics import resolve_cutoff


class TestBacktestMode:
    def test_backtest_cutoff_is_as_of_time(self):
        as_of = datetime(2025, 6, 15, 15, 0, tzinfo=timezone.utc)
        cutoff = resolve_cutoff(TimeMode.BACKTEST, as_of, None)
        assert cutoff == as_of

    def test_backtest_cutoff_does_not_exceed_as_of(self):
        as_of = datetime(2025, 6, 15, 15, 0, tzinfo=timezone.utc)
        cutoff = resolve_cutoff(TimeMode.BACKTEST, as_of, None)
        assert cutoff <= as_of

    def test_backtest_with_earlier_cutoff(self):
        as_of = datetime(2025, 6, 15, 15, 0, tzinfo=timezone.utc)
        earlier = as_of - timedelta(days=1)
        cutoff = resolve_cutoff(TimeMode.BACKTEST, as_of, earlier)
        assert cutoff == earlier

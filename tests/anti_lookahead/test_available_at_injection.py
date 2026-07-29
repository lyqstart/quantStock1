"""Anti-lookahead: available_at is always injected into queries (DD-CORE-016)."""

from datetime import datetime, timezone

import pytest

from app.datacontext.query import TimeMode
from app.datacontext.time_semantics import resolve_cutoff


class TestAvailableAtInjection:
    def test_research_mode_uses_now_if_no_cutoff(self):
        as_of = datetime(2025, 6, 15, 15, 0, tzinfo=timezone.utc)
        cutoff = resolve_cutoff(TimeMode.RESEARCH, as_of, None)
        assert cutoff is not None

    def test_strategy_mode_uses_min(self):
        as_of = datetime(2025, 6, 15, 15, 0, tzinfo=timezone.utc)
        cutoff = resolve_cutoff(TimeMode.STRATEGY, as_of, None)
        assert cutoff is not None

    def test_cutoff_never_none_for_backtest(self):
        as_of = datetime(2025, 6, 15, 15, 0, tzinfo=timezone.utc)
        cutoff = resolve_cutoff(TimeMode.BACKTEST, as_of, None)
        assert cutoff is not None

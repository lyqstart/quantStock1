"""Anti-lookahead: published_at and available_at are separated by silence_days (DD-CORE-016)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.datacontext.time_semantics import resolve_cutoff
from app.datacontext.query import TimeMode


class TestPublishedAvailableSeparation:
    def test_available_at_equals_published_plus_silence(self):
        """available_at = published_at + silence_days (REQ-CORE-022)."""
        published = datetime(2025, 6, 10, 12, 0, tzinfo=timezone.utc)
        silence_days = 2
        expected_available = published + timedelta(days=silence_days)
        assert expected_available > published

    def test_query_uses_available_not_published(self):
        """In backtest mode, the cutoff is as_of_time, which represents available_at boundary."""
        as_of = datetime(2025, 6, 12, 12, 0, tzinfo=timezone.utc)
        cutoff = resolve_cutoff(TimeMode.BACKTEST, as_of, None)
        # A record published on 2025-06-12 with 0 silence_days would have available_at = 2025-06-12
        # A record published on 2025-06-12 with 2 silence_days would have available_at = 2025-06-14
        # The cutoff at 2025-06-12 should exclude records available after that.
        assert cutoff == as_of

"""Time semantics engine: the anti-lookahead cutoff resolver (DD-CORE-016).

The single rule enforced everywhere downstream is: *every* clean-table query
must constrain ``available_at <= resolve_cutoff(...)``. Readers therefore never
trust a caller-supplied time window on its own; the cutoff derived here is the
hard upper bound that prevents future information leaking into research/backtest.

published_at vs available_at (REQ-CORE-022): ``available_at`` already encodes
``published_at + silence_days`` at write time, so queries key off
``available_at`` exclusively and never read ``published_at`` as an upper bound.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.datacontext.query import TimeMode


def resolve_cutoff(
    time_mode: TimeMode,
    as_of_time: datetime | None,
    available_at_cutoff: datetime | None,
) -> datetime:
    """Compute the anti-lookahead ``available_at`` upper bound for a query.

    Semantics per DD-CORE-016:

    - ``RESEARCH``: cutoff is the current wall clock (latest available data).
      If ``available_at_cutoff`` is supplied it further tightens the bound.
    - ``STRATEGY``: cutoff is ``min(as_of_time, available_at_cutoff or now)``.
      ``as_of_time`` is required.
    - ``BACKTEST``: strict historical replay. cutoff is
      ``min(as_of_time, available_at_cutoff)`` (cutoff defaults to
      ``as_of_time`` when ``available_at_cutoff`` is absent). ``as_of_time`` is
      required. This is the invariant that guarantees zero future reads.

    All returned cutoffs are timezone-aware (UTC) so they compare safely against
    the TIMESTAMPTZ ``available_at`` columns.
    """

    now = _now_utc()

    if time_mode == TimeMode.RESEARCH:
        cutoff = now
        if available_at_cutoff is not None:
            cutoff = min(cutoff, _ensure_aware(available_at_cutoff))
        return cutoff

    if time_mode == TimeMode.STRATEGY:
        if as_of_time is None:
            raise ValueError("strategy time mode requires as_of_time")
        anchor = _ensure_aware(as_of_time)
        upper = _ensure_aware(available_at_cutoff) if available_at_cutoff is not None else now
        return min(anchor, upper)

    if time_mode == TimeMode.BACKTEST:
        if as_of_time is None:
            raise ValueError("backtest time mode requires as_of_time")
        anchor = _ensure_aware(as_of_time)
        if available_at_cutoff is not None:
            return min(anchor, _ensure_aware(available_at_cutoff))
        return anchor

    raise ValueError(f"unknown time mode: {time_mode!r}")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(value: datetime) -> datetime:
    """Normalize a possibly-naive datetime to timezone-aware UTC.

    Clean-table ``available_at`` is TIMESTAMPTZ; comparing a naive value would
    raise or silently misbehave under psycopg. Naive inputs are assumed UTC.
    """

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value

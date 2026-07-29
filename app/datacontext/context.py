"""DataContext: the single read entry-point over the CLEAN layer (DD-CORE-014).

DataContext composes the value objects, time semantics, readers and the
adjustment/alignment helpers into a small, ergonomic API. It deliberately
imports ONLY ``clean``/``meta`` schema models (never ``raw``) and routes every
query through :func:`resolve_cutoff` so the anti-lookahead bound is always
enforced (REQ-CORE-009 / CP-CORE-006).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.datacontext.adjustment import apply_adjustment
from app.datacontext.alignment import align_to_calendar
from app.datacontext.query import (
    AdjustmentMethod,
    Frequency,
    QualityPolicy,
    QueryContext,
    SecurityScope,
    TimeMode,
)
from app.datacontext.readers import _as_dict_list, read_daily, read_events, read_financial, read_minute, resolve_security_codes
from app.datacontext.time_semantics import resolve_cutoff
from app.storage.models.clean import CleanStockAdjFactor, CleanTradeCalendar


class DataContext:
    """Read-only facade over CLEAN data with anti-lookahead guarantees."""

    def __init__(self, session: Session, time_mode: TimeMode = TimeMode.RESEARCH):
        self._session = session
        self._time_mode = time_mode

    # -- daily -------------------------------------------------------------

    def query_daily(
        self,
        security_scope: SecurityScope | str | Sequence[str],
        start_date: date | None = None,
        end_date: date | None = None,
        as_of_time: datetime | None = None,
        adjustment: AdjustmentMethod = AdjustmentMethod.NONE,
        quality: QualityPolicy = QualityPolicy.STANDARD,
        frequency: Frequency = Frequency.DAILY,
        available_at_cutoff: datetime | None = None,
    ) -> list[dict[str, Any]]:
        scope = _coerce_scope(security_scope)
        ctx = QueryContext(
            security_scope=scope,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            as_of_time=as_of_time,
            available_at_cutoff=available_at_cutoff,
            time_mode=self._time_mode,
            adjustment_method=adjustment,
            quality_policy=quality,
        )
        rows = read_daily(self._session, ctx)

        if adjustment != AdjustmentMethod.NONE:
            factors = self._read_adj_factors(scope, ctx)
            rows = apply_adjustment(rows, factors, adjustment)

        if frequency in (Frequency.WEEKLY, Frequency.MONTHLY):
            calendar = self._read_calendar(ctx)
            rows = align_to_calendar(rows, calendar, frequency)

        return rows

    # -- minute -----------------------------------------------------------

    def query_minute(
        self,
        security_scope: SecurityScope | str | Sequence[str],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        frequency: Frequency | str = Frequency.MINUTE_1,
        as_of_time: datetime | None = None,
        quality: QualityPolicy = QualityPolicy.STANDARD,
        available_at_cutoff: datetime | None = None,
    ) -> list[dict[str, Any]]:
        scope = _coerce_scope(security_scope)
        ctx = QueryContext(
            security_scope=scope,
            frequency=_coerce_frequency(frequency),
            start_time=start_time,
            end_time=end_time,
            as_of_time=as_of_time,
            available_at_cutoff=available_at_cutoff,
            time_mode=self._time_mode,
            quality_policy=quality,
        )
        return read_minute(self._session, ctx)

    # -- financial --------------------------------------------------------

    def query_financial(
        self,
        security_scope: SecurityScope | str | Sequence[str],
        report_type: str = "income",
        as_of_time: datetime | None = None,
        revision: int | None = None,
        quality: QualityPolicy = QualityPolicy.STANDARD,
        available_at_cutoff: datetime | None = None,
    ) -> list[dict[str, Any]]:
        scope = _coerce_scope(security_scope)
        ctx = QueryContext(
            security_scope=scope,
            as_of_time=as_of_time,
            available_at_cutoff=available_at_cutoff,
            time_mode=self._time_mode,
            quality_policy=quality,
            report_type=report_type,
            revision_version=revision,
        )
        return read_financial(self._session, ctx)

    # -- events -----------------------------------------------------------

    def query_events(
        self,
        security_scope: SecurityScope | str | Sequence[str],
        event_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        as_of_time: datetime | None = None,
        quality: QualityPolicy = QualityPolicy.STANDARD,
        available_at_cutoff: datetime | None = None,
    ) -> list[dict[str, Any]]:
        scope = _coerce_scope(security_scope)
        ctx = QueryContext(
            security_scope=scope,
            as_of_time=as_of_time,
            available_at_cutoff=available_at_cutoff,
            time_mode=self._time_mode,
            quality_policy=quality,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
        )
        return read_events(self._session, ctx)

    # -- internals --------------------------------------------------------

    def _read_adj_factors(self, scope: SecurityScope, ctx: QueryContext) -> list[dict[str, Any]]:
        cutoff = resolve_cutoff(ctx.time_mode, ctx.as_of_time, ctx.available_at_cutoff)
        stmt = select(CleanStockAdjFactor).where(CleanStockAdjFactor.available_at <= cutoff)
        codes = resolve_security_codes(scope)
        if codes is not None:
            stmt = stmt.where(CleanStockAdjFactor.security_code.in_(codes))
        if ctx.start_date is not None:
            stmt = stmt.where(CleanStockAdjFactor.trade_date >= ctx.start_date)
        if ctx.end_date is not None:
            stmt = stmt.where(CleanStockAdjFactor.trade_date <= ctx.end_date)
        return _as_dict_list(self._session.execute(stmt).mappings().all())

    def _read_calendar(self, ctx: QueryContext) -> list[Any]:
        cutoff = resolve_cutoff(ctx.time_mode, ctx.as_of_time, ctx.available_at_cutoff)
        stmt = select(CleanTradeCalendar.calendar_date).where(
            CleanTradeCalendar.available_at <= cutoff,
            CleanTradeCalendar.is_open.is_(True),
        )
        if ctx.start_date is not None:
            stmt = stmt.where(CleanTradeCalendar.calendar_date >= ctx.start_date)
        if ctx.end_date is not None:
            stmt = stmt.where(CleanTradeCalendar.calendar_date <= ctx.end_date)
        return [row[0] for row in self._session.execute(stmt).all()]


def _coerce_scope(value: SecurityScope | str | Sequence[str]) -> SecurityScope:
    if isinstance(value, SecurityScope):
        return value
    if isinstance(value, str):
        return SecurityScope(mode="single", codes=[value])
    if isinstance(value, (list, tuple)):
        codes = [str(item) for item in value]
        if not codes:
            raise ValueError("security scope received an empty code list")
        mode = "single" if len(codes) == 1 else "pool"
        return SecurityScope(mode=mode, codes=codes)
    raise TypeError(f"unsupported security scope type: {type(value).__name__}")


def _coerce_frequency(value: Frequency | str) -> Frequency:
    if isinstance(value, Frequency):
        return value
    if isinstance(value, str):
        try:
            return Frequency(value)
        except ValueError as exc:
            raise ValueError(f"unsupported frequency: {value!r}") from exc
    raise TypeError(f"unsupported frequency type: {type(value).__name__}")

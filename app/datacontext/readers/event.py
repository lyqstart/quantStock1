"""Event reader for ``clean.stock_suspend_event`` and ``clean.stock_limit_price``.

These tables record historical corporate-event state at a point in time
(REQ-CORE-023): suspend/limit status is queried *as-of* a cutoff rather than
read from ``SecurityMaster.list_status`` (which only reflects the present).

Mandatory behaviour:
  - inject ``available_at <= cutoff`` (anti-lookahead);
  - apply the requested :class:`QualityPolicy`;
  - honour an optional ``event_type`` selector (``suspend`` / ``limit_price``;
    ``None`` merges both families).

Only ``app.storage.models.clean`` is imported.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.datacontext.query import QueryContext
from app.datacontext.readers import _as_dict_list, build_quality_clause, resolve_security_codes
from app.datacontext.time_semantics import resolve_cutoff
from app.storage.models.clean import CleanStockLimitPrice, CleanStockSuspendEvent


def read_events(session: Session, query_ctx: QueryContext) -> list[dict[str, Any]]:
    """Return event rows (suspend and/or limit-price) as-of the cutoff."""

    cutoff = resolve_cutoff(
        query_ctx.time_mode,
        query_ctx.as_of_time,
        query_ctx.available_at_cutoff,
    )
    codes = resolve_security_codes(query_ctx.security_scope)
    event_type = query_ctx.event_type

    rows: list[dict[str, Any]] = []
    if event_type in (None, "suspend"):
        rows.extend(_read_suspend(session, query_ctx, cutoff, codes))
    if event_type in (None, "limit_price"):
        rows.extend(_read_limit_price(session, query_ctx, cutoff, codes))
    return rows


def _read_suspend(
    session: Session,
    query_ctx: QueryContext,
    cutoff,
    codes: list[str] | None,
) -> list[dict[str, Any]]:
    stmt = select(CleanStockSuspendEvent).where(
        CleanStockSuspendEvent.available_at <= cutoff,
        build_quality_clause(CleanStockSuspendEvent.quality_status, query_ctx.quality_policy),
    )
    if codes is not None:
        stmt = stmt.where(CleanStockSuspendEvent.security_code.in_(codes))
    if query_ctx.start_date is not None:
        stmt = stmt.where(CleanStockSuspendEvent.trade_date >= query_ctx.start_date)
    if query_ctx.end_date is not None:
        stmt = stmt.where(CleanStockSuspendEvent.trade_date <= query_ctx.end_date)
    stmt = stmt.order_by(CleanStockSuspendEvent.security_code, CleanStockSuspendEvent.trade_date)
    return _as_dict_list(session.execute(stmt).mappings().all())


def _read_limit_price(
    session: Session,
    query_ctx: QueryContext,
    cutoff,
    codes: list[str] | None,
) -> list[dict[str, Any]]:
    stmt = select(CleanStockLimitPrice).where(
        CleanStockLimitPrice.available_at <= cutoff,
        build_quality_clause(CleanStockLimitPrice.quality_status, query_ctx.quality_policy),
    )
    if codes is not None:
        stmt = stmt.where(CleanStockLimitPrice.security_code.in_(codes))
    if query_ctx.start_date is not None:
        stmt = stmt.where(CleanStockLimitPrice.trade_date >= query_ctx.start_date)
    if query_ctx.end_date is not None:
        stmt = stmt.where(CleanStockLimitPrice.trade_date <= query_ctx.end_date)
    stmt = stmt.order_by(CleanStockLimitPrice.security_code, CleanStockLimitPrice.trade_date)
    return _as_dict_list(session.execute(stmt).mappings().all())

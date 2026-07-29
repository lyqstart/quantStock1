"""Minute reader for ``clean.stock_minute`` (DD-CORE-014 / REQ-CORE-017, REQ-CORE-028).

Mandatory behaviour:
  - REJECT ``full_market`` scans (raises ``ValueError``) to avoid sequential
    scans of the minute hypertable (REQ-CORE-028);
  - inject ``available_at <= resolve_cutoff(...)`` (anti-lookahead);
  - apply the requested :class:`QualityPolicy`.

Only ``app.storage.models.clean`` is imported.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.datacontext.query import QueryContext
from app.datacontext.readers import _as_dict_list, build_quality_clause
from app.datacontext.time_semantics import resolve_cutoff
from app.storage.models.clean import CleanStockMinute


def read_minute(session: Session, query_ctx: QueryContext) -> list[dict[str, Any]]:
    """Return minute bars for a single code or explicit pool.

    Raises ``ValueError`` for full-market scans.
    """

    if query_ctx.security_scope.is_full_market:
        raise ValueError("Full market minute scan is not allowed")

    cutoff = resolve_cutoff(
        query_ctx.time_mode,
        query_ctx.as_of_time,
        query_ctx.available_at_cutoff,
    )

    stmt = select(CleanStockMinute).where(
        CleanStockMinute.available_at <= cutoff,
        build_quality_clause(CleanStockMinute.quality_status, query_ctx.quality_policy),
    )

    codes = query_ctx.security_scope.codes or []
    if codes:
        stmt = stmt.where(CleanStockMinute.security_code.in_(list(codes)))
    if query_ctx.frequency.value != "daily":
        # Minute hypertable is partitioned by trade_time; narrow by frequency.
        stmt = stmt.where(CleanStockMinute.frequency == query_ctx.frequency.value)

    if query_ctx.start_time is not None:
        stmt = stmt.where(CleanStockMinute.trade_time >= query_ctx.start_time)
    if query_ctx.end_time is not None:
        stmt = stmt.where(CleanStockMinute.trade_time <= query_ctx.end_time)

    stmt = stmt.order_by(CleanStockMinute.security_code, CleanStockMinute.trade_time)
    return _as_dict_list(session.execute(stmt).mappings().all())

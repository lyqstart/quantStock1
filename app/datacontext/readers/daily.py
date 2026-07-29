"""Daily reader for ``clean.stock_daily`` (DD-CORE-014 / REQ-CORE-017).

Mandatory behaviour:
  - injects ``available_at <= resolve_cutoff(...)`` (anti-lookahead, REQ-CORE-009);
  - applies the requested :class:`QualityPolicy` (FAILED always blocked);
  - honours :class:`SecurityScope` (single / pool / full_market).

This module imports ONLY ``app.storage.models.clean``. Importing
``app.storage.models.raw`` is forbidden by contract (see ``.importlinter``).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.datacontext.query import QueryContext
from app.datacontext.readers import _as_dict_list, build_quality_clause, resolve_security_codes
from app.datacontext.time_semantics import resolve_cutoff
from app.storage.models.clean import CleanStockDaily


def read_daily(session: Session, query_ctx: QueryContext) -> list[dict[str, Any]]:
    """Return daily OHLCV rows honouring the anti-lookahead cutoff."""

    cutoff = resolve_cutoff(
        query_ctx.time_mode,
        query_ctx.as_of_time,
        query_ctx.available_at_cutoff,
    )

    stmt = select(CleanStockDaily).where(
        CleanStockDaily.available_at <= cutoff,
        build_quality_clause(CleanStockDaily.quality_status, query_ctx.quality_policy),
    )

    codes = resolve_security_codes(query_ctx.security_scope)
    if codes is not None:
        stmt = stmt.where(CleanStockDaily.security_code.in_(codes))

    if query_ctx.start_date is not None:
        stmt = stmt.where(CleanStockDaily.trade_date >= query_ctx.start_date)
    if query_ctx.end_date is not None:
        stmt = stmt.where(CleanStockDaily.trade_date <= query_ctx.end_date)

    stmt = stmt.order_by(CleanStockDaily.security_code, CleanStockDaily.trade_date)
    return _as_dict_list(session.execute(stmt).mappings().all())

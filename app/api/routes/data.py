"""Unified read-only data query API (DD-CORE-017 / REQ-CORE-025-028).

Thin wrappers around :class:`DataContext` that:
- enforce a per-request ``statement_timeout`` (REQ-CORE-027);
- return a :class:`DataResponse` with :class:`DataSemantics` metadata (REQ-CORE-026);
- reject full-market minute scans (REQ-CORE-028);
- sanitize errors so no stacks/keys/tokens leak.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.schemas.data import (
    DailyQueryRequest,
    DataResponse,
    DataSemantics,
    ErrorResponse,
    EventQueryRequest,
    FinancialQueryRequest,
    MinuteQueryRequest,
)
from app.core.config import get_settings
from app.datacontext.context import DataContext
from app.datacontext.query import (
    AdjustmentMethod,
    Frequency,
    QualityPolicy,
    SecurityScope,
    TimeMode,
)
from app.storage.db import get_session_factory
from app.storage.models.clean import CleanTradeCalendar, SecurityMaster

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data", tags=["data"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# The API exposes the Chinese-market adjustment vocabulary (qfq/hfq) while the
# DataContext AdjustmentMethod enum uses forward_adj/backward_adj. Both forms are
# accepted so the raw enum value stays usable too.
_ADJUSTMENT_MAP: dict[str, AdjustmentMethod] = {
    "none": AdjustmentMethod.NONE,
    "qfq": AdjustmentMethod.FORWARD_ADJ,
    "hfq": AdjustmentMethod.BACKWARD_ADJ,
    "forward_adj": AdjustmentMethod.FORWARD_ADJ,
    "backward_adj": AdjustmentMethod.BACKWARD_ADJ,
}


def _coerce_adjustment(value: str) -> AdjustmentMethod:
    if value in _ADJUSTMENT_MAP:
        return _ADJUSTMENT_MAP[value]
    raise ValueError(f"unsupported adjustment: {value!r}")


def _get_session() -> Session:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def _apply_statement_timeout(session: Session) -> int:
    """Set LOCAL statement_timeout for this transaction (REQ-CORE-027)."""
    timeout_ms = int(get_settings().query_timeout_seconds * 1000)
    session.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))
    return timeout_ms


def _build_metadata(
    *,
    data_source: str,
    quality_policy: str,
    as_of_time: datetime | None = None,
    row_count: int = 0,
    adjustment_policy: str | None = None,
) -> DataSemantics:
    cutoff = as_of_time or datetime.now(timezone.utc)
    return DataSemantics(
        data_source=data_source,
        quality_policy=quality_policy,
        available_at_cutoff=cutoff,
        row_count=row_count,
        adjustment_policy=adjustment_policy,
    )


def _to_response(
    rows: list[dict],
    *,
    data_source: str,
    quality_policy: str,
    as_of_time: datetime | None = None,
    adjustment_policy: str | None = None,
) -> DataResponse:
    metadata = _build_metadata(
        data_source=data_source,
        quality_policy=quality_policy,
        as_of_time=as_of_time,
        row_count=len(rows),
        adjustment_policy=adjustment_policy,
    )
    return DataResponse(rows=rows, metadata=metadata)


def _coerce_scope(
    security_codes: list[str] | None,
    full_market: bool,
) -> SecurityScope | str | list[str]:
    """Map request fields to DataContext's security_scope parameter."""
    if full_market:
        return SecurityScope(mode="full_market")
    if security_codes:
        return security_codes if len(security_codes) > 1 else security_codes[0]
    raise ValueError("either security_codes or full_market must be specified")


def _handle_error(exc: Exception, timeout_ms: int) -> None:
    """Translate exceptions to sanitized HTTP errors (no stacks/keys)."""
    if isinstance(exc, OperationalError) and "statement timeout" in str(exc).lower():
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=ErrorResponse(
                error_code="QUERY_TIMEOUT",
                message=f"query exceeded {timeout_ms}ms statement_timeout",
            ).model_dump(),
        ) from exc
    logger.exception("data query failed")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="an internal error occurred",
        ).model_dump(),
    ) from exc


# ---------------------------------------------------------------------------
# Daily
# ---------------------------------------------------------------------------

@router.post("/daily", response_model=DataResponse)
def query_daily(
    request: DailyQueryRequest,
    session: Session = Depends(_get_session),
) -> DataResponse:
    timeout_ms = _apply_statement_timeout(session)
    try:
        scope = _coerce_scope(request.security_codes, request.full_market)
        ctx = DataContext(session)
        rows = ctx.query_daily(
            security_scope=scope,
            start_date=request.start_date,
            end_date=request.end_date,
            as_of_time=request.as_of_time,
            adjustment=_coerce_adjustment(request.adjustment),
            quality=QualityPolicy(request.quality),
            frequency=Frequency(request.frequency),
        )
        return _to_response(
            rows,
            data_source="clean.stock_daily",
            quality_policy=request.quality,
            as_of_time=request.as_of_time,
            adjustment_policy=request.adjustment if request.adjustment != "none" else None,
        )
    except Exception as exc:
        _handle_error(exc, timeout_ms)


# ---------------------------------------------------------------------------
# Minute
# ---------------------------------------------------------------------------

@router.post("/minute", response_model=DataResponse)
def query_minute(
    request: MinuteQueryRequest,
    session: Session = Depends(_get_session),
) -> DataResponse:
    if not request.security_codes or len(request.security_codes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="MISSING_SECURITY_CODES",
                message="minute query requires at least one security_code",
            ).model_dump(),
        )
    if len(request.security_codes) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="TOO_MANY_SECURITIES",
                message="minute query supports at most 100 securities per request",
            ).model_dump(),
        )
    timeout_ms = _apply_statement_timeout(session)
    try:
        ctx = DataContext(session)
        rows = ctx.query_minute(
            security_scope=request.security_codes,
            start_time=request.start_time,
            end_time=request.end_time,
            frequency=Frequency(request.frequency),
            as_of_time=request.as_of_time,
            quality=QualityPolicy(request.quality),
        )
        return _to_response(
            rows,
            data_source="clean.stock_minute",
            quality_policy=request.quality,
            as_of_time=request.as_of_time,
        )
    except Exception as exc:
        _handle_error(exc, timeout_ms)


# ---------------------------------------------------------------------------
# Financial
# ---------------------------------------------------------------------------

@router.post("/financial", response_model=DataResponse)
def query_financial(
    request: FinancialQueryRequest,
    session: Session = Depends(_get_session),
) -> DataResponse:
    timeout_ms = _apply_statement_timeout(session)
    try:
        scope = _coerce_scope(request.security_codes, request.full_market)
        ctx = DataContext(session)
        rows = ctx.query_financial(
            security_scope=scope,
            report_type=request.report_type,
            as_of_time=request.as_of_time,
            revision=request.revision,
            quality=QualityPolicy(request.quality),
        )
        table = f"clean.financial_{request.report_type}"
        return _to_response(
            rows,
            data_source=table,
            quality_policy=request.quality,
            as_of_time=request.as_of_time,
        )
    except Exception as exc:
        _handle_error(exc, timeout_ms)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@router.post("/events", response_model=DataResponse)
def query_events(
    request: EventQueryRequest,
    session: Session = Depends(_get_session),
) -> DataResponse:
    timeout_ms = _apply_statement_timeout(session)
    try:
        scope = _coerce_scope(request.security_codes, request.full_market)
        ctx = DataContext(session)
        rows = ctx.query_events(
            security_scope=scope,
            event_type=request.event_type,
            start_date=request.start_date,
            end_date=request.end_date,
            as_of_time=request.as_of_time,
            quality=QualityPolicy(request.quality),
        )
        return _to_response(
            rows,
            data_source="clean.stock_suspend_event",
            quality_policy=request.quality,
            as_of_time=request.as_of_time,
        )
    except Exception as exc:
        _handle_error(exc, timeout_ms)


# ---------------------------------------------------------------------------
# Calendar (direct clean model query — lightweight)
# ---------------------------------------------------------------------------

@router.get("/calendar", response_model=DataResponse)
def query_calendar(
    exchange: str = Query("SSE"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(_get_session),
) -> DataResponse:
    try:
        stmt = select(CleanTradeCalendar).where(
            CleanTradeCalendar.exchange_code == exchange,
            CleanTradeCalendar.is_open.is_(True),
        )
        if start:
            stmt = stmt.where(CleanTradeCalendar.calendar_date >= start)
        if end:
            stmt = stmt.where(CleanTradeCalendar.calendar_date <= end)
        rows = [
            {
                "exchange_code": r.exchange_code,
                "calendar_date": r.calendar_date.isoformat() if r.calendar_date else None,
                "is_open": r.is_open,
            }
            for r in session.scalars(stmt).all()
        ]
        return _to_response(
            rows,
            data_source="clean.trade_calendar",
            quality_policy="standard",
        )
    except Exception as exc:
        _handle_error(exc, 30000)


# ---------------------------------------------------------------------------
# Securities (direct clean model query — lightweight)
# ---------------------------------------------------------------------------

@router.get("/securities", response_model=DataResponse)
def query_securities(
    active_only: bool = Query(True),
    session: Session = Depends(_get_session),
) -> DataResponse:
    try:
        stmt = select(SecurityMaster)
        if active_only:
            # SecurityMaster has no is_active flag; list_status "L" == listed/active
            # (tushare vocabulary: L=listed, D=delisted, P=paused).
            stmt = stmt.where(SecurityMaster.list_status == "L")
        rows = [
            {
                "security_code": r.security_code,
                "name": r.name,
                "exchange_code": r.exchange_code,
                "list_status": r.list_status,
            }
            for r in session.scalars(stmt.limit(10000)).all()
        ]
        return _to_response(
            rows,
            data_source="clean.security_master",
            quality_policy="standard",
        )
    except Exception as exc:
        _handle_error(exc, 30000)

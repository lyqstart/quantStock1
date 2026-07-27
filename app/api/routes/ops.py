from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.collect.market_data_service import (
    enqueue_financial_item,
    enqueue_stock_basic,
    enqueue_stock_daily,
    enqueue_stock_minute,
    enqueue_trade_date_item,
)
from app.collect.trade_calendar_service import enqueue_trade_calendar
from app.ops.service import (
    cancel_task,
    get_overview,
    get_task,
    list_data_items,
    list_schedulers,
    list_tasks,
    list_workers,
    pause_task,
    record_audit,
    resume_task,
    retry_task,
)
from app.storage.db import get_db_session

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])
SHANGHAI = ZoneInfo("Asia/Shanghai")
TRADE_DATE_ITEMS = {
    "stock_daily",
    "stock_adj_factor",
    "stock_daily_basic",
    "stock_suspend",
    "stock_limit_price",
}


class ReasonBody(BaseModel):
    reason: str | None = None


class BackfillBody(BaseModel):
    data_item: Literal[
        "trade_calendar",
        "stock_basic",
        "stock_daily",
        "stock_adj_factor",
        "stock_daily_basic",
        "stock_suspend",
        "stock_limit_price",
        "stock_minute",
        "financial_income",
        "financial_indicator",
    ]
    reason: str
    trade_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    ts_code: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    frequency: str = "1min"
    exchange: str = "SSE"


def _require(value, message: str):
    if value is None:
        raise HTTPException(status_code=422, detail=message)
    return value


@router.get("/overview")
def overview(session: Session = Depends(get_db_session)) -> dict[str, object]:
    return get_overview(session)


@router.get("/data-items")
def data_items(session: Session = Depends(get_db_session)) -> list[dict[str, object]]:
    return list_data_items(session)


@router.get("/tasks")
def tasks(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
) -> list[dict[str, object]]:
    return list_tasks(session, limit=limit)


@router.get("/tasks/{task_id}")
def task_detail(task_id: uuid.UUID, session: Session = Depends(get_db_session)) -> dict[str, object]:
    result = get_task(session, task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="task not found")
    return result


@router.get("/workers")
def workers(session: Session = Depends(get_db_session)) -> list[dict[str, object]]:
    return list_workers(session)


@router.get("/scheduler")
def scheduler(session: Session = Depends(get_db_session)) -> list[dict[str, object]]:
    return list_schedulers(session)


@router.post("/backfills")
def create_backfill(
    body: BackfillBody,
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    try:
        if body.data_item == "trade_calendar":
            task, created = enqueue_trade_calendar(
                session,
                start_date=_require(body.start_date, "start_date is required"),
                end_date=_require(body.end_date, "end_date is required"),
                exchange=body.exchange,
                run_type="BACKFILL",
                reason=body.reason,
            )
        elif body.data_item == "stock_basic":
            task, created = enqueue_stock_basic(session, run_type="BACKFILL", reason=body.reason)
        elif body.data_item in TRADE_DATE_ITEMS:
            day = _require(body.trade_date, "trade_date is required")
            if body.data_item == "stock_daily":
                task, created = enqueue_stock_daily(
                    session,
                    trade_date=day,
                    run_type="BACKFILL",
                    requested_by="operator",
                    reason=body.reason,
                )
            else:
                task, created = enqueue_trade_date_item(
                    session,
                    item_code=body.data_item,
                    trade_date=day,
                    run_type="BACKFILL",
                    requested_by="operator",
                    reason=body.reason,
                )
        elif body.data_item == "stock_minute":
            task, created = enqueue_stock_minute(
                session,
                ts_code=_require(body.ts_code, "ts_code is required"),
                start_time=_require(body.start_time, "start_time is required"),
                end_time=_require(body.end_time, "end_time is required"),
                frequency=body.frequency,
                run_type="BACKFILL",
                requested_by="operator",
                reason=body.reason,
            )
        else:
            task, created = enqueue_financial_item(
                session,
                item_code=body.data_item,
                ts_code=_require(body.ts_code, "ts_code is required"),
                start_date=_require(body.start_date, "start_date is required"),
                end_date=_require(body.end_date, "end_date is required"),
                run_type="BACKFILL",
                requested_by="operator",
                reason=body.reason,
            )
        record_audit(
            session,
            object_type="collect_task",
            object_id=str(task.task_id),
            action="backfill_create",
            after_status=task.status,
            reason=body.reason,
            trace_id=task.trace_id,
            metadata={"data_item": body.data_item, "created": created},
        )
        session.commit()
        return {"task_id": str(task.task_id), "created": created, "status": task.status}
    except HTTPException:
        session.rollback()
        raise
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _apply_action(session: Session, action, task_id: uuid.UUID, **kwargs) -> dict[str, object]:
    try:
        task = action(session, task_id=task_id, **kwargs)
        if task is None:
            raise HTTPException(status_code=404, detail="task not found")
        session.commit()
        return {"task_id": str(task.task_id), "status": task.status}
    except HTTPException:
        session.rollback()
        raise
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/retry")
def retry(
    task_id: uuid.UUID,
    body: ReasonBody,
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    return _apply_action(session, retry_task, task_id, reason=body.reason)


@router.post("/tasks/{task_id}/pause")
def pause(
    task_id: uuid.UUID,
    body: ReasonBody,
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    return _apply_action(session, pause_task, task_id, reason=body.reason)


@router.post("/tasks/{task_id}/resume")
def resume(task_id: uuid.UUID, session: Session = Depends(get_db_session)) -> dict[str, object]:
    return _apply_action(session, resume_task, task_id)


@router.post("/tasks/{task_id}/cancel")
def cancel(
    task_id: uuid.UUID,
    body: ReasonBody,
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    return _apply_action(session, cancel_task, task_id, reason=body.reason)

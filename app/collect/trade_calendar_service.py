from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collect.idempotency import build_task_idempotency_key
from app.collect.planners.trade_calendar import plan_trade_calendar_slices
from app.collect.repository import TaskRepository
from app.storage.models.meta import DataItem, SourceBinding
from app.storage.models.ops import CollectTask, RequestSlice

SHANGHAI = ZoneInfo("Asia/Shanghai")


def enqueue_trade_calendar(
    session: Session,
    *,
    start_date: date,
    end_date: date,
    exchange: str = "SSE",
    run_type: str = "BACKFILL",
    requested_by: str = "operator",
    reason: str = "trade calendar collection",
) -> tuple[CollectTask, bool]:
    item = session.scalar(select(DataItem).where(DataItem.code == "trade_calendar"))
    binding = session.scalar(select(SourceBinding).where(SourceBinding.binding_code == "tushare:trade_calendar"))
    if item is None or binding is None:
        raise RuntimeError("trade_calendar catalog is not initialized")
    if not binding.enabled:
        raise RuntimeError("tushare:trade_calendar binding is disabled")

    start_dt = datetime.combine(start_date, time.min, tzinfo=SHANGHAI)
    end_dt = datetime.combine(end_date, time.max, tzinfo=SHANGHAI)
    object_scope = {"type": "exchange", "exchange": exchange}
    idempotency_key = build_task_idempotency_key(
        data_item_code=item.code,
        source_binding_code=binding.binding_code,
        run_type=run_type,
        object_scope=object_scope,
        time_start=start_dt,
        time_end=end_dt,
        frequency="day",
    )
    task = CollectTask(
        data_item_id=item.data_item_id,
        source_binding_id=binding.source_binding_id,
        run_type=run_type,
        object_scope=object_scope,
        time_start=start_dt,
        time_end=end_dt,
        frequency="day",
        priority=20 if run_type == "BACKFILL" else 0,
        status="PENDING",
        idempotency_key=idempotency_key,
        requested_by=requested_by,
        reason=reason,
        source_binding_version=binding.request_policy_version,
        planning_status="COMPLETE",
        planning_complete=True,
    )
    persisted, created = TaskRepository(session).create_task_idempotent(task)
    if not created:
        return persisted, False

    plans = plan_trade_calendar_slices(
        start_date=start_date,
        end_date=end_date,
        exchange=exchange,
        source_binding_code=binding.binding_code,
        mapping_version=binding.field_mapping_version,
    )
    for plan in plans:
        session.add(
            RequestSlice(
                task_id=persisted.task_id,
                partition_key=plan.partition_key,
                slice_order=plan.slice_order,
                request_params=plan.request_params,
                request_hash=plan.request_hash,
                time_start=datetime.combine(plan.start_date, time.min, tzinfo=SHANGHAI),
                time_end=datetime.combine(plan.end_date, time.max, tzinfo=SHANGHAI),
                object_key=exchange,
                frequency="day",
                status="PENDING",
                priority=persisted.priority,
            )
        )
    session.flush()
    return persisted, True

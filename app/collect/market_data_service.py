from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collect.idempotency import build_task_idempotency_key
from app.collect.planners.stock_basic import plan_stock_basic_slices
from app.collect.planners.trade_date_item import plan_trade_date_slice
from app.collect.repository import TaskRepository
from app.storage.models.meta import DataItem, SourceBinding
from app.storage.models.ops import CollectTask, RequestSlice, TaskDefinition

SHANGHAI = ZoneInfo("Asia/Shanghai")
TRADE_DATE_ITEMS = {
    "stock_daily",
    "stock_adj_factor",
    "stock_daily_basic",
    "stock_suspend",
    "stock_limit_price",
}


def _catalog(session: Session, code: str) -> tuple[DataItem, SourceBinding]:
    item = session.scalar(select(DataItem).where(DataItem.code == code))
    binding = session.scalar(select(SourceBinding).where(SourceBinding.binding_code == f"tushare:{code}"))
    if item is None or binding is None:
        raise RuntimeError(f"{code} catalog is not initialized")
    if not binding.enabled:
        raise RuntimeError(f"tushare:{code} binding is disabled")
    return item, binding


def enqueue_stock_basic(
    session: Session,
    *,
    run_type: str = "INITIALIZE",
    requested_by: str = "operator",
    reason: str = "stock basic collection",
) -> tuple[CollectTask, bool]:
    item, binding = _catalog(session, "stock_basic")
    object_scope = {"type": "market", "market": "CN_A", "list_statuses": ["L", "D", "P", "G"]}
    key = build_task_idempotency_key(
        data_item_code=item.code,
        source_binding_code=binding.binding_code,
        run_type=run_type,
        object_scope=object_scope,
        frequency=None,
    )
    task = CollectTask(
        data_item_id=item.data_item_id,
        source_binding_id=binding.source_binding_id,
        run_type=run_type,
        object_scope=object_scope,
        priority=10 if run_type == "INITIALIZE" else 20,
        status="PENDING",
        idempotency_key=key,
        requested_by=requested_by,
        reason=reason,
        source_binding_version=binding.request_policy_version,
        planning_status="COMPLETE",
        planning_complete=True,
    )
    persisted, created = TaskRepository(session).create_task_idempotent(task)
    if not created:
        return persisted, False

    for plan in plan_stock_basic_slices(
        source_binding_code=binding.binding_code,
        mapping_version=binding.field_mapping_version,
    ):
        session.add(
            RequestSlice(
                task_id=persisted.task_id,
                partition_key=plan.partition_key,
                slice_order=plan.slice_order,
                request_params=plan.request_params,
                request_hash=plan.request_hash,
                object_key=plan.request_params["list_status"],
                status="PENDING",
                priority=persisted.priority,
            )
        )
    session.flush()
    return persisted, True


def enqueue_trade_date_item(
    session: Session,
    *,
    item_code: str,
    trade_date: date,
    run_type: str = "INCREMENTAL",
    requested_by: str = "scheduler",
    reason: str | None = None,
) -> tuple[CollectTask, bool]:
    if item_code not in TRADE_DATE_ITEMS:
        raise ValueError(f"Unsupported trade-date DataItem: {item_code}")

    item, binding = _catalog(session, item_code)
    definition = session.scalar(
        select(TaskDefinition).where(TaskDefinition.task_code == f"{item_code}_incremental")
    )
    start_dt = datetime.combine(trade_date, time.min, tzinfo=SHANGHAI)
    end_dt = datetime.combine(trade_date, time.max, tzinfo=SHANGHAI)
    object_scope = {"type": "market", "market": "CN_A"}
    frequency = item.frequency or "day"
    key = build_task_idempotency_key(
        data_item_code=item.code,
        source_binding_code=binding.binding_code,
        run_type=run_type,
        object_scope=object_scope,
        time_start=start_dt,
        time_end=end_dt,
        frequency=frequency,
    )
    task = CollectTask(
        task_definition_id=definition.task_definition_id if definition is not None and run_type == "INCREMENTAL" else None,
        data_item_id=item.data_item_id,
        source_binding_id=binding.source_binding_id,
        run_type=run_type,
        object_scope=object_scope,
        time_start=start_dt,
        time_end=end_dt,
        frequency=frequency,
        priority=(definition.priority if definition is not None else 0) if run_type == "INCREMENTAL" else 20,
        status="PENDING",
        idempotency_key=key,
        requested_by=requested_by,
        reason=reason or f"{item_code} collection",
        definition_version=definition.definition_version if definition is not None and run_type == "INCREMENTAL" else None,
        source_binding_version=binding.request_policy_version,
        expected_business_time=end_dt,
        planning_status="COMPLETE",
        planning_complete=True,
    )
    persisted, created = TaskRepository(session).create_task_idempotent(task)
    if not created:
        return persisted, False

    pagination_mode = str((binding.config or {}).get("pagination_mode", ""))
    page_size = None
    if pagination_mode == "offset":
        configured_page_size = int((binding.config or {}).get("page_size") or binding.max_rows_per_request or 0)
        if configured_page_size <= 0:
            raise RuntimeError(f"{binding.binding_code} offset pagination requires a positive page size")
        page_size = configured_page_size

    plan = plan_trade_date_slice(
        trade_date=trade_date,
        source_binding_code=binding.binding_code,
        api_name=binding.api_name,
        mapping_version=binding.field_mapping_version,
        page_size=page_size,
    )
    session.add(
        RequestSlice(
            task_id=persisted.task_id,
            partition_key=plan.partition_key,
            slice_order=plan.slice_order,
            request_params=plan.request_params,
            request_hash=plan.request_hash,
            time_start=start_dt,
            time_end=end_dt,
            object_key="CN_A",
            frequency=frequency,
            status="PENDING",
            priority=persisted.priority,
        )
    )
    session.flush()
    return persisted, True


def enqueue_stock_daily(
    session: Session,
    *,
    trade_date: date,
    run_type: str = "INCREMENTAL",
    requested_by: str = "scheduler",
    reason: str = "scheduled stock daily collection",
) -> tuple[CollectTask, bool]:
    return enqueue_trade_date_item(
        session,
        item_code="stock_daily",
        trade_date=trade_date,
        run_type=run_type,
        requested_by=requested_by,
        reason=reason,
    )

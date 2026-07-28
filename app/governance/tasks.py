from __future__ import annotations

import uuid
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.collect.idempotency import canonical_json, sha256_text
from app.collect.repository import TaskRepository
from app.storage.models.clean import CleanBatch
from app.storage.models.meta import DataItem
from app.storage.models.raw import (
    RawBatch,
    TushareAdjFactor,
    TushareDaily,
    TushareDailyBasic,
    TushareStkLimit,
    TushareStockBasic,
    TushareSuspendD,
    TushareTradeCal,
)
from app.storage.models.ops import CollectRun, CollectTask, RequestSlice, TaskDefinition

SHANGHAI = ZoneInfo("Asia/Shanghai")
P4_ITEMS = {
    "trade_calendar",
    "stock_basic",
    "stock_daily",
    "stock_adj_factor",
    "stock_daily_basic",
    "stock_suspend",
    "stock_limit_price",
}
P4_RAW_MODELS = {
    "trade_calendar": TushareTradeCal,
    "stock_basic": TushareStockBasic,
    "stock_daily": TushareDaily,
    "stock_adj_factor": TushareAdjFactor,
    "stock_daily_basic": TushareDailyBasic,
    "stock_suspend": TushareSuspendD,
    "stock_limit_price": TushareStkLimit,
}
P4_TRADE_DATE_ITEMS = {
    "stock_daily",
    "stock_adj_factor",
    "stock_daily_basic",
    "stock_suspend",
    "stock_limit_price",
}
MAPPING_VERSION = "mapping-v1"
NORMALIZATION_VERSION = "normalization-v3"
QUALITY_RULE_VERSION = "quality-v3"


def _has_physical_raw(item_code: str):
    raw_model = P4_RAW_MODELS[item_code]
    return exists(
        select(1)
        .select_from(CollectRun)
        .join(RawBatch, RawBatch.run_id == CollectRun.run_id)
        .join(raw_model, raw_model.raw_batch_id == RawBatch.raw_batch_id)
        .where(
            CollectRun.task_id == CollectTask.task_id,
            RawBatch.status == "SUCCEEDED",
        )
    )


def _scope_for_source_task(item_code: str, task: CollectTask) -> tuple[str, dict]:
    if item_code == "trade_calendar":
        exchange = str(task.object_scope.get("exchange", "SSE"))
        start = task.time_start.astimezone(SHANGHAI).date().isoformat() if task.time_start else None
        end = task.time_end.astimezone(SHANGHAI).date().isoformat() if task.time_end else None
        scope = {"exchange_code": exchange, "start_date": start, "end_date": end}
        return f"exchange:{exchange}|start:{start}|end:{end}", scope
    if item_code == "stock_basic":
        return "GLOBAL", {"market": "CN_A"}
    if item_code in P4_TRADE_DATE_ITEMS:
        if task.time_start is None:
            raise ValueError(f"{item_code} source task has no trade date")
        day = task.time_start.astimezone(SHANGHAI).date().isoformat()
        return f"trade_date:{day.replace('-', '')}", {"trade_date": day, "market": "CN_A"}
    raise ValueError(f"P4 clean is not implemented for {item_code}")


def _definition(session: Session, stage: str, item_code: str) -> TaskDefinition:
    definition = session.scalar(
        select(TaskDefinition).where(TaskDefinition.task_code == f"{stage}:{item_code}")
    )
    if definition is None:
        raise RuntimeError(f"P4 task definition missing: {stage}:{item_code}")
    return definition


def _enqueue_stage_task(
    session: Session,
    *,
    stage: str,
    item: DataItem,
    definition: TaskDefinition,
    source_binding_id: uuid.UUID,
    source_id: uuid.UUID,
    source_kind: str,
    scope_key: str,
    scope_json: dict,
    run_type: str,
    trace_id: uuid.UUID,
    time_start: datetime | None,
    time_end: datetime | None,
    frequency: str | None,
    requested_by: str,
    reason: str,
) -> tuple[CollectTask, bool]:
    object_scope = {
        "stage": stage.upper(),
        "source_kind": source_kind,
        "source_id": str(source_id),
        "scope_key": scope_key,
        "scope": scope_json,
    }
    idempotency_key = sha256_text(
        canonical_json(
            {
                "stage": stage,
                "data_item": item.code,
                "source_kind": source_kind,
                "source_id": str(source_id),
                "scope_key": scope_key,
                "run_type": run_type,
                "mapping_version": MAPPING_VERSION,
                "normalization_version": NORMALIZATION_VERSION,
                "quality_rule_version": QUALITY_RULE_VERSION,
            }
        )
    )
    task = CollectTask(
        task_definition_id=definition.task_definition_id,
        data_item_id=item.data_item_id,
        source_binding_id=source_binding_id,
        run_type=run_type,
        object_scope=object_scope,
        time_start=time_start,
        time_end=time_end,
        frequency=frequency,
        priority=definition.priority,
        status="PENDING",
        idempotency_key=idempotency_key,
        requested_by=requested_by,
        reason=reason,
        trace_id=trace_id,
        definition_version=definition.definition_version,
        source_binding_version=None,
        update_policy_version="p4-v1",
        planning_status="COMPLETE",
        planning_complete=True,
    )
    persisted, created = TaskRepository(session).create_task_idempotent(task)
    if not created:
        return persisted, False

    params = {
        "stage": stage.upper(),
        "source_kind": source_kind,
        "source_id": str(source_id),
        "scope_key": scope_key,
        "scope": scope_json,
        "mapping_version": MAPPING_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "quality_rule_version": QUALITY_RULE_VERSION,
    }
    session.add(
        RequestSlice(
            task_id=persisted.task_id,
            partition_key=f"{stage}:{source_kind}:{source_id}",
            slice_order=0,
            request_params=params,
            request_hash=sha256_text(canonical_json(params)),
            time_start=time_start,
            time_end=time_end,
            object_key=scope_key,
            frequency=frequency,
            status="PENDING",
            priority=persisted.priority,
        )
    )
    session.flush()
    return persisted, True


def enqueue_clean_for_collect_task(
    session: Session,
    source_task: CollectTask,
    *,
    requested_by: str = "system",
    reason: str = "automatic P4 clean after collection",
) -> tuple[CollectTask, bool] | None:
    item = session.get(DataItem, source_task.data_item_id)
    if item is None or item.code not in P4_ITEMS:
        return None
    if source_task.status != "SUCCEEDED":
        raise ValueError("source collection task must be SUCCEEDED before cleaning")
    scope_key, scope_json = _scope_for_source_task(item.code, source_task)
    return _enqueue_stage_task(
        session,
        stage="clean",
        item=item,
        definition=_definition(session, "clean", item.code),
        source_binding_id=source_task.source_binding_id,
        source_id=source_task.task_id,
        source_kind="collect_task",
        scope_key=scope_key,
        scope_json=scope_json,
        run_type=source_task.run_type,
        trace_id=source_task.trace_id,
        time_start=source_task.time_start,
        time_end=source_task.time_end,
        frequency=source_task.frequency,
        requested_by=requested_by,
        reason=reason,
    )


def enqueue_quality_for_clean_batch(
    session: Session,
    *,
    clean_task: CollectTask,
    clean_batch: CleanBatch,
    requested_by: str = "system",
    reason: str = "automatic P4 quality after cleaning",
) -> tuple[CollectTask, bool]:
    item = session.get(DataItem, clean_task.data_item_id)
    if item is None:
        raise RuntimeError("clean task data item missing")
    return _enqueue_stage_task(
        session,
        stage="quality",
        item=item,
        definition=_definition(session, "quality", item.code),
        source_binding_id=clean_task.source_binding_id,
        source_id=clean_batch.clean_batch_id,
        source_kind="clean_batch",
        scope_key=clean_batch.scope_key,
        scope_json=dict(clean_batch.scope_json),
        run_type=clean_task.run_type,
        trace_id=clean_task.trace_id,
        time_start=clean_task.time_start,
        time_end=clean_task.time_end,
        frequency=clean_task.frequency,
        requested_by=requested_by,
        reason=reason,
    )


def enqueue_clean_latest(
    session: Session,
    *,
    item_code: str,
    trade_date: date | None = None,
    requested_by: str = "operator",
    reason: str = "manual P4 clean from existing RAW",
) -> tuple[CollectTask, bool]:
    if item_code not in P4_ITEMS:
        raise ValueError(f"P4 clean is not implemented for {item_code}")
    item = session.scalar(select(DataItem).where(DataItem.code == item_code))
    if item is None:
        raise RuntimeError(f"DataItem missing: {item_code}")

    stmt = select(CollectTask).where(
        CollectTask.data_item_id == item.data_item_id,
        CollectTask.status == "SUCCEEDED",
        ~CollectTask.object_scope.has_key("stage"),  # noqa: E711 - PostgreSQL JSONB operator
    )
    # Empty suspend_d responses are meaningful (no suspension event on that day),
    # so they may be cleaned from a successful zero-row RawBatch. Other P4 items
    # must have physical RAW rows to avoid selecting idempotent duplicate batches.
    if item_code != "stock_suspend":
        stmt = stmt.where(_has_physical_raw(item_code))
    if item_code in P4_TRADE_DATE_ITEMS:
        if trade_date is None:
            raise ValueError(f"trade_date is required for {item_code}")
        start = datetime.combine(trade_date, time.min, tzinfo=SHANGHAI)
        end = datetime.combine(trade_date, time.max, tzinfo=SHANGHAI)
        stmt = stmt.where(CollectTask.time_start >= start, CollectTask.time_start <= end)
    source_task = session.scalar(stmt.order_by(CollectTask.finished_at.desc()).limit(1))
    if source_task is None:
        raise ValueError(f"no SUCCEEDED collection task found for {item_code}")
    result = enqueue_clean_for_collect_task(
        session,
        source_task,
        requested_by=requested_by,
        reason=reason,
    )
    if result is None:  # pragma: no cover
        raise RuntimeError(f"unsupported P4 item: {item_code}")

    clean_task, created = result
    if not created and clean_task.status == "SUCCEEDED":
        scope_key, _scope_json = _scope_for_source_task(item_code, source_task)
        existing_batch = session.scalar(
            select(CleanBatch)
            .where(
                CleanBatch.data_item_id == item.data_item_id,
                CleanBatch.scope_key == scope_key,
                CleanBatch.mapping_version == MAPPING_VERSION,
                CleanBatch.normalization_version == NORMALIZATION_VERSION,
                CleanBatch.source_task_id == source_task.task_id,
            )
            .order_by(CleanBatch.created_at.desc())
            .limit(1)
        )
        if (
            existing_batch is not None
            and existing_batch.status in {"CANDIDATE", "VALIDATING", "BLOCKED"}
            and existing_batch.quality_rule_version != QUALITY_RULE_VERSION
        ):
            enqueue_quality_for_clean_batch(
                session,
                clean_task=clean_task,
                clean_batch=existing_batch,
                requested_by=requested_by,
                reason=f"quality rerun after rule version change: {QUALITY_RULE_VERSION}",
            )

    return clean_task, created

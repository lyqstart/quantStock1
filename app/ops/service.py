from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.storage.models.audit import AuditEvent
from app.storage.models.meta import DataItem, SourceBinding
from app.storage.models.ops import (
    CollectTask,
    DataWatermark,
    RequestSlice,
    SchedulerState,
    WorkerRegistry,
)

ACTIVE_TASK_STATES = {"PENDING", "RUNNING", "PARTIAL"}
RETRYABLE_TASK_STATES = {"FAILED", "PARTIAL"}
PAUSABLE_TASK_STATES = {"PENDING", "RUNNING", "PARTIAL"}



def record_audit(
    session: Session,
    *,
    object_type: str,
    object_id: str,
    action: str,
    before_status: str | None = None,
    after_status: str | None = None,
    reason: str | None = None,
    trace_id: uuid.UUID | None = None,
    actor_id: str = "operator",
    metadata: dict | None = None,
) -> None:
    session.add(
        AuditEvent(
            object_type=object_type,
            object_id=object_id,
            action=action,
            before_status=before_status,
            after_status=after_status,
            reason=reason,
            actor_type="user",
            actor_id=actor_id,
            trace_id=trace_id,
            metadata_json=metadata or {},
        )
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def get_overview(session: Session, *, now: datetime | None = None) -> dict[str, object]:
    current = now or datetime.now(UTC)
    worker_cutoff = current - timedelta(minutes=2)
    scheduler_cutoff = current - timedelta(minutes=2)

    workers_online = int(
        session.scalar(
            select(func.count())
            .select_from(WorkerRegistry)
            .where(WorkerRegistry.status.in_(("ONLINE", "DRAINING")), WorkerRegistry.heartbeat_at >= worker_cutoff)
        )
        or 0
    )
    scheduler_online = int(
        session.scalar(
            select(func.count())
            .select_from(SchedulerState)
            .where(
                SchedulerState.status.in_(("LEADER", "STANDBY")),
                SchedulerState.heartbeat_at >= scheduler_cutoff,
            )
        )
        or 0
    )
    running = int(
        session.scalar(
            select(func.count()).select_from(CollectTask).where(CollectTask.status == "RUNNING")
        )
        or 0
    )
    pending = int(
        session.scalar(
            select(func.count()).select_from(CollectTask).where(CollectTask.status == "PENDING")
        )
        or 0
    )
    failed = int(
        session.scalar(
            select(func.count()).select_from(CollectTask).where(CollectTask.status == "FAILED")
        )
        or 0
    )

    if workers_online <= 0 or scheduler_online <= 0:
        system_status = "DEGRADED"
    elif failed > 0:
        system_status = "DEGRADED"
    else:
        system_status = "HEALTHY"

    return {
        "system_status": system_status,
        "workers_online": workers_online,
        "scheduler_online": scheduler_online > 0,
        "tasks_running": running,
        "tasks_pending": pending,
        "tasks_failed": failed,
    }


def list_data_items(session: Session) -> list[dict[str, object]]:
    items = list(session.scalars(select(DataItem).order_by(DataItem.code.asc())))
    result: list[dict[str, object]] = []
    for item in items:
        watermarks = list(
            session.scalars(
                select(DataWatermark)
                .where(DataWatermark.data_item_id == item.data_item_id)
                .order_by(DataWatermark.updated_at.desc())
            )
        )
        latest = watermarks[0] if watermarks else None
        binding = session.scalar(
            select(SourceBinding)
            .where(SourceBinding.data_item_id == item.data_item_id, SourceBinding.priority == 1)
            .order_by(SourceBinding.created_at.asc())
            .limit(1)
        )
        result.append(
            {
                "code": item.code,
                "name": item.name,
                "critical": item.critical,
                "status": item.status,
                "capability_status": binding.capability_status if binding else None,
                "latest_collected_at": _iso(latest.latest_collected_at) if latest else None,
                "latest_clean_at": _iso(latest.latest_clean_at) if latest else None,
                "latest_quality_passed_at": _iso(latest.latest_quality_passed_at) if latest else None,
                "scope_key": latest.scope_key if latest else None,
                "frequency": latest.frequency if latest else item.frequency,
            }
        )
    return result


def list_tasks(session: Session, *, limit: int = 50) -> list[dict[str, object]]:
    rows = session.execute(
        select(CollectTask, DataItem.code)
        .join(DataItem, DataItem.data_item_id == CollectTask.data_item_id)
        .order_by(CollectTask.created_at.desc())
        .limit(max(1, min(limit, 200)))
    ).all()
    return [
        {
            "task_id": str(task.task_id),
            "data_item": code,
            "run_type": task.run_type,
            "status": task.status,
            "priority": task.priority,
            "created_at": _iso(task.created_at),
            "started_at": _iso(task.started_at),
            "finished_at": _iso(task.finished_at),
            "last_error_type": task.last_error_type,
            "last_error_message": task.last_error_message,
        }
        for task, code in rows
    ]


def get_task(session: Session, task_id: uuid.UUID) -> dict[str, object] | None:
    row = session.execute(
        select(CollectTask, DataItem.code)
        .join(DataItem, DataItem.data_item_id == CollectTask.data_item_id)
        .where(CollectTask.task_id == task_id)
    ).first()
    if row is None:
        return None
    task, code = row
    counts = dict(
        session.execute(
            select(RequestSlice.status, func.count())
            .where(RequestSlice.task_id == task_id)
            .group_by(RequestSlice.status)
        ).all()
    )
    return {
        "task_id": str(task.task_id),
        "data_item": code,
        "run_type": task.run_type,
        "status": task.status,
        "object_scope": task.object_scope,
        "time_start": _iso(task.time_start),
        "time_end": _iso(task.time_end),
        "frequency": task.frequency,
        "reason": task.reason,
        "requested_by": task.requested_by,
        "last_error_type": task.last_error_type,
        "last_error_message": task.last_error_message,
        "slice_counts": counts,
    }


def list_workers(session: Session) -> list[dict[str, object]]:
    workers = list(session.scalars(select(WorkerRegistry).order_by(WorkerRegistry.started_at.desc())))
    return [
        {
            "worker_id": row.worker_id,
            "environment": row.environment,
            "status": row.status,
            "version": row.version,
            "hostname": row.hostname,
            "started_at": _iso(row.started_at),
            "heartbeat_at": _iso(row.heartbeat_at),
        }
        for row in workers
    ]


def list_schedulers(session: Session) -> list[dict[str, object]]:
    rows = list(session.scalars(select(SchedulerState).order_by(SchedulerState.started_at.desc())))
    return [
        {
            "scheduler_id": row.scheduler_id,
            "environment": row.environment,
            "status": row.status,
            "version": row.version,
            "started_at": _iso(row.started_at),
            "heartbeat_at": _iso(row.heartbeat_at),
            "last_scan_at": _iso(row.last_scan_at),
            "next_scan_at": _iso(row.next_scan_at),
        }
        for row in rows
    ]


def pause_task(session: Session, *, task_id: uuid.UUID, reason: str | None = None) -> CollectTask | None:
    task = session.get(CollectTask, task_id)
    if task is None:
        return None
    if task.status not in PAUSABLE_TASK_STATES:
        raise ValueError(f"task cannot be paused from status {task.status}")
    before = task.status
    task.status = "PAUSED"
    task.paused_at = datetime.now(UTC)
    task.pause_reason = reason
    record_audit(
        session, object_type="collect_task", object_id=str(task.task_id), action="pause",
        before_status=before, after_status=task.status, reason=reason, trace_id=task.trace_id,
    )
    session.flush()
    return task


def resume_task(session: Session, *, task_id: uuid.UUID) -> CollectTask | None:
    task = session.get(CollectTask, task_id)
    if task is None:
        return None
    if task.status != "PAUSED":
        raise ValueError(f"task cannot be resumed from status {task.status}")
    before = task.status
    task.status = "PENDING"
    task.paused_at = None
    task.pause_reason = None
    record_audit(
        session, object_type="collect_task", object_id=str(task.task_id), action="resume",
        before_status=before, after_status=task.status, trace_id=task.trace_id,
    )
    session.flush()
    return task


def cancel_task(session: Session, *, task_id: uuid.UUID, reason: str | None = None) -> CollectTask | None:
    task = session.get(CollectTask, task_id)
    if task is None:
        return None
    if task.status in {"SUCCEEDED", "CANCELLED"}:
        raise ValueError(f"task cannot be cancelled from status {task.status}")
    now = datetime.now(UTC)
    before = task.status
    task.status = "CANCELLED"
    task.cancel_requested_at = now
    task.finished_at = now
    session.execute(
        update(RequestSlice)
        .where(
            RequestSlice.task_id == task_id,
            RequestSlice.status.in_(("PENDING", "RETRY_WAIT")),
        )
        .values(status="CANCELLED", next_retry_at=None)
    )
    record_audit(
        session, object_type="collect_task", object_id=str(task.task_id), action="cancel",
        before_status=before, after_status=task.status, reason=reason, trace_id=task.trace_id,
    )
    session.flush()
    return task


def retry_task(session: Session, *, task_id: uuid.UUID, reason: str | None = None) -> CollectTask | None:
    task = session.get(CollectTask, task_id)
    if task is None:
        return None
    if task.status not in RETRYABLE_TASK_STATES:
        raise ValueError(f"task cannot be retried from status {task.status}")
    failed_count = int(
        session.scalar(
            select(func.count())
            .select_from(RequestSlice)
            .where(RequestSlice.task_id == task_id, RequestSlice.status.in_(("FAILED", "LOST")))
        )
        or 0
    )
    if failed_count <= 0:
        raise ValueError("task has no failed slices to retry")
    session.execute(
        update(RequestSlice)
        .where(RequestSlice.task_id == task_id, RequestSlice.status.in_(("FAILED", "LOST")))
        .values(
            status="PENDING",
            next_retry_at=None,
            leased_by=None,
            leased_at=None,
            lease_expires_at=None,
            lease_token=None,
        )
    )
    before = task.status
    task.status = "PENDING"
    task.finished_at = None
    task.last_error_type = None
    task.last_error_message = None
    record_audit(
        session, object_type="collect_task", object_id=str(task.task_id), action="retry",
        before_status=before, after_status=task.status, reason=reason, trace_id=task.trace_id,
    )
    session.flush()
    return task

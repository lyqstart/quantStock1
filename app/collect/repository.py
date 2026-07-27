import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.storage.models.meta import SourceBinding
from app.storage.models.ops import CollectTask, RequestSlice


@dataclass(frozen=True)
class ClaimedSlice:
    slice_id: uuid.UUID
    task_id: uuid.UUID
    lease_token: uuid.UUID
    request_params: dict
    request_hash: str


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_task_idempotent(self, task: CollectTask) -> tuple[CollectTask, bool]:
        try:
            with self.session.begin_nested():
                self.session.add(task)
                self.session.flush()
            return task, True
        except IntegrityError:
            existing = self.session.scalar(
                select(CollectTask).where(
                    CollectTask.idempotency_version == task.idempotency_version,
                    CollectTask.idempotency_key == task.idempotency_key,
                )
            )
            if existing is None:
                raise
            return existing, False

    def claim_next_slice(self, *, worker_id: str, lease_seconds: int = 60) -> ClaimedSlice | None:
        now = datetime.now(UTC)
        stmt: Select[tuple[RequestSlice]] = (
            select(RequestSlice)
            .join(CollectTask, CollectTask.task_id == RequestSlice.task_id)
            .join(SourceBinding, SourceBinding.source_binding_id == CollectTask.source_binding_id)
            .where(
                CollectTask.status.in_(("PENDING", "RUNNING", "PARTIAL")),
                SourceBinding.enabled.is_(True),
                SourceBinding.capability_status.not_in(("permission_denied", "schema_changed", "temporarily_unavailable")),
                RequestSlice.status.in_(("PENDING", "RETRY_WAIT")),
                or_(RequestSlice.next_retry_at.is_(None), RequestSlice.next_retry_at <= now),
            )
            .order_by(RequestSlice.priority.asc(), RequestSlice.slice_order.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        slice_row = self.session.scalar(stmt)
        if slice_row is None:
            return None

        token = uuid.uuid4()
        slice_row.status = "RUNNING"
        slice_row.leased_by = worker_id
        slice_row.leased_at = now
        slice_row.heartbeat_at = now
        slice_row.lease_expires_at = now + timedelta(seconds=lease_seconds)
        slice_row.lease_token = token
        slice_row.attempt_count += 1
        self.session.flush()
        return ClaimedSlice(
            slice_id=slice_row.slice_id,
            task_id=slice_row.task_id,
            lease_token=token,
            request_params=dict(slice_row.request_params),
            request_hash=slice_row.request_hash,
        )

    def heartbeat_slice(self, *, slice_id: uuid.UUID, lease_token: uuid.UUID, lease_seconds: int = 60) -> bool:
        now = datetime.now(UTC)
        result = self.session.execute(
            update(RequestSlice)
            .where(
                RequestSlice.slice_id == slice_id,
                RequestSlice.lease_token == lease_token,
                RequestSlice.status == "RUNNING",
            )
            .values(heartbeat_at=now, lease_expires_at=now + timedelta(seconds=lease_seconds))
        )
        return result.rowcount == 1

    def complete_slice(self, *, slice_id: uuid.UUID, lease_token: uuid.UUID, response_rows: int) -> bool:
        now = datetime.now(UTC)
        result = self.session.execute(
            update(RequestSlice)
            .where(
                RequestSlice.slice_id == slice_id,
                RequestSlice.lease_token == lease_token,
                RequestSlice.status == "RUNNING",
            )
            .values(
                status="SUCCEEDED",
                response_rows=response_rows,
                lease_expires_at=None,
                heartbeat_at=now,
            )
        )
        return result.rowcount == 1

    def release_slice_for_retry(
        self,
        *,
        slice_id: uuid.UUID,
        lease_token: uuid.UUID,
        error_type: str,
        next_retry_at: datetime,
    ) -> bool:
        result = self.session.execute(
            update(RequestSlice)
            .where(
                RequestSlice.slice_id == slice_id,
                RequestSlice.lease_token == lease_token,
                RequestSlice.status == "RUNNING",
            )
            .values(
                status="RETRY_WAIT",
                last_error_type=error_type,
                next_retry_at=next_retry_at,
                leased_by=None,
                leased_at=None,
                lease_expires_at=None,
                lease_token=None,
            )
        )
        return result.rowcount == 1

    def fail_slice(
        self,
        *,
        slice_id: uuid.UUID,
        lease_token: uuid.UUID,
        error_type: str,
    ) -> bool:
        result = self.session.execute(
            update(RequestSlice)
            .where(
                RequestSlice.slice_id == slice_id,
                RequestSlice.lease_token == lease_token,
                RequestSlice.status == "RUNNING",
            )
            .values(
                status="FAILED",
                last_error_type=error_type,
                leased_by=None,
                leased_at=None,
                lease_expires_at=None,
                lease_token=None,
            )
        )
        return result.rowcount == 1

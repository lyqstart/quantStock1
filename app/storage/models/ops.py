import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, BigInteger, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.models.base import Base


class TaskDefinition(Base):
    __tablename__ = "task_definition"
    __table_args__ = {"schema": "ops"}
    task_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    data_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.data_item.data_item_id"), nullable=False)
    source_binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.source_binding.source_binding_id"), nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    update_mode: Mapped[str | None] = mapped_column(String(32))
    schedule_rule: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    availability_rule: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    split_policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    retry_policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=30)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    definition_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CollectTask(Base):
    __tablename__ = "collect_task"
    __table_args__ = (
        UniqueConstraint("idempotency_version", "idempotency_key", name="uq_collect_task_idempotency"),
        {"schema": "ops"},
    )
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_definition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.task_definition.task_definition_id"))
    data_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.data_item.data_item_id"), nullable=False)
    source_binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.source_binding.source_binding_id"), nullable=False)
    run_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    time_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    frequency: Mapped[str | None] = mapped_column(String(16))
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=30)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_task.task_id"))
    gap_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    requested_by: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    definition_version: Mapped[str | None] = mapped_column(String(32))
    source_binding_version: Mapped[str | None] = mapped_column(String(32))
    update_policy_version: Mapped[str | None] = mapped_column(String(32))
    expected_business_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planning_status: Mapped[str] = mapped_column(String(16), nullable=False, default="NOT_STARTED")
    planning_cursor: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    planning_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pause_reason: Mapped[str | None] = mapped_column(Text)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_type: Mapped[str | None] = mapped_column(String(64))
    last_error_message: Mapped[str | None] = mapped_column(Text)


class CollectRun(Base):
    __tablename__ = "collect_run"
    __table_args__ = (UniqueConstraint("task_id", "run_number", name="uq_collect_run_task_number"), {"schema": "ops"})
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_task.task_id"), nullable=False)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CREATED")
    worker_id: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_type: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_of_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_run.run_id"))
    retry_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_policy_version: Mapped[str | None] = mapped_column(String(32))
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RequestSlice(Base):
    __tablename__ = "request_slice"
    __table_args__ = (UniqueConstraint("task_id", "partition_key", name="uq_request_slice_task_partition"), {"schema": "ops"})
    slice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_task.task_id"), nullable=False)
    partition_key: Mapped[str] = mapped_column(String(256), nullable=False)
    slice_order: Mapped[int] = mapped_column(BigInteger, nullable=False)
    request_params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    time_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    object_key: Mapped[str | None] = mapped_column(String(128))
    frequency: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=30)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_rows: Mapped[int | None] = mapped_column(Integer)
    last_error_type: Mapped[str | None] = mapped_column(String(64))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_slice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.request_slice.slice_id"))
    split_depth: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    leased_by: Mapped[str | None] = mapped_column(String(128))
    leased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SliceAttempt(Base):
    __tablename__ = "slice_attempt"
    __table_args__ = (UniqueConstraint("slice_id", "attempt_no", name="uq_slice_attempt_slice_number"), {"schema": "ops"})
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.request_slice.slice_id"), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_run.run_id"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source_binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.source_binding.source_binding_id"), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    response_rows: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    rate_limit_wait_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    provider_request_id: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkerRegistry(Base):
    __tablename__ = "worker_registry"
    __table_args__ = {"schema": "ops"}
    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    worker_type: Mapped[str] = mapped_column(String(32), nullable=False, default="collect")
    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    process_id: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    current_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class SchedulerState(Base):
    __tablename__ = "scheduler_state"
    __table_args__ = {"schema": "ops"}
    scheduler_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class DataWatermark(Base):
    __tablename__ = "data_watermark"
    __table_args__ = (UniqueConstraint("data_item_id", "scope_key", "frequency", name="uq_data_watermark_scope"), {"schema": "ops"})
    watermark_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.data_item.data_item_id"), nullable=False)
    source_binding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.source_binding.source_binding_id"))
    scope_key: Mapped[str] = mapped_column(String(256), nullable=False)
    frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    initialized_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    initialized_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_clean_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_quality_passed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TaskCheckpoint(Base):
    __tablename__ = "task_checkpoint"
    __table_args__ = {"schema": "ops"}
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_task.task_id"), nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_run.run_id"))
    checkpoint_type: Mapped[str] = mapped_column(String(32), nullable=False)
    checkpoint_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    completed_units: Mapped[int | None] = mapped_column(BigInteger)
    total_units: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RateLimitState(Base):
    __tablename__ = "rate_limit_state"
    __table_args__ = {"schema": "ops"}
    rate_limit_key: Mapped[str] = mapped_column(String(256), primary_key=True)
    source_binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.source_binding.source_binding_id"), nullable=False)
    window_type: Mapped[str] = mapped_column(String(16), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    effective_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CircuitBreakerState(Base):
    __tablename__ = "circuit_breaker_state"
    __table_args__ = {"schema": "ops"}
    source_binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.source_binding.source_binding_id"), primary_key=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="CLOSED")
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    half_open_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_type: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

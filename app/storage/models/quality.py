import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.models.base import Base


class QualityRun(Base):
    __tablename__ = "quality_run"
    __table_args__ = {"schema": "quality"}

    quality_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_task.task_id"), nullable=False)
    clean_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clean.clean_batch.clean_batch_id"), nullable=False)
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    app_version: Mapped[str] = mapped_column(String(64), nullable=False)
    code_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    rules_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rules_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rules_warned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rules_blocked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    issues_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gaps_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class QualityIssue(Base):
    __tablename__ = "quality_issue"
    __table_args__ = {"schema": "quality"}

    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quality_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quality.quality_run.quality_run_id"), nullable=False)
    data_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.data_item.data_item_id"), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    scope_key: Mapped[str] = mapped_column(String(512), nullable=False)
    scope_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    issue_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    expected_value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_type: Mapped[str | None] = mapped_column(String(32))
    resolved_by_quality_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    related_gap_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    repair_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    auto_repair_exhausted: Mapped[bool] = mapped_column(nullable=False, default=False)
    next_repair_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_repair_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DataGap(Base):
    __tablename__ = "data_gap"
    __table_args__ = {"schema": "quality"}

    gap_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.data_item.data_item_id"), nullable=False)
    gap_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    scope_key: Mapped[str] = mapped_column(String(512), nullable=False)
    scope_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    discovered_by_quality_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quality.quality_run.quality_run_id"), nullable=False)
    discovered_by_issue_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolved_by_quality_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class IssueTaskLink(Base):
    __tablename__ = "issue_task_link"
    __table_args__ = (
        UniqueConstraint("issue_id", "task_id", name="uq_issue_task_link"),
        {"schema": "quality"},
    )

    issue_task_link_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quality.quality_issue.issue_id"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_task.task_id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

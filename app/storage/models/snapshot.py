"""ORM mapping for the immutable data snapshot tables (DD-CORE-015 / TASK-001).

``clean.data_snapshot`` and ``clean.data_snapshot_input`` are created by
migration 0013. The snapshot captures a frozen, reproducible view of a set of
CLEAN inputs as-of a point in time. Once a snapshot reaches ``READY`` it is
immutable (a DB trigger + application-layer discipline guarantee this).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.models.base import Base


class DataSnapshot(Base):
    __tablename__ = "data_snapshot"
    __table_args__ = {"schema": "clean"}

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="BUILDING")
    as_of_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at_cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_item_codes: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    quality_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    adjustment_policy: Mapped[str] = mapped_column(String(32), nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    skipped_failed_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    warning_published_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    warning_excluded_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    supersedes_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clean.data_snapshot.snapshot_id"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataSnapshotInput(Base):
    __tablename__ = "data_snapshot_input"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "clean_batch_id", name="uq_data_snapshot_input"),
        {"schema": "clean"},
    )

    input_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clean.data_snapshot.snapshot_id"),
        nullable=False,
    )
    clean_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clean.clean_batch.clean_batch_id"),
        nullable=False,
    )
    input_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at_cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

"""LineageEdge ORM model.

Maps the `lineage.lineage_edge` table created by migration 0013.
Backed by DD-CORE-011 and REQ-CORE-013.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.models.base import Base


class LineageEdge(Base):
    """A directed edge between two data-platform objects.

    `source_type`/`target_type` are coarse object categories such as
    ``raw_batch``, ``clean_batch``, ``quality_run``, ``data_snapshot``. The
    corresponding ``*_id`` columns hold the UUID of the referenced row in the
    typed table; there is intentionally no DB-level FK because edges can span
    many tables and we want the lineage layer to remain forward-compatible.
    """

    __tablename__ = "lineage_edge"
    __table_args__ = (
        Index("ix_lineage_edge_source", "source_type", "source_id"),
        Index("ix_lineage_edge_target", "target_type", "target_id"),
        Index("ix_lineage_edge_type", "edge_type"),
        {"schema": "lineage"},
    )

    edge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_key: Mapped[str | None] = mapped_column(String(512))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

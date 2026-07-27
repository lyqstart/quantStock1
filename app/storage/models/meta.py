import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.models.base import Base


class DataSource(Base):
    __tablename__ = "data_source"
    __table_args__ = {"schema": "meta"}

    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="enabled")
    credential_ref: Mapped[str | None] = mapped_column(String(128))
    base_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    health_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DataItem(Base):
    __tablename__ = "data_item"
    __table_args__ = {"schema": "meta"}

    data_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    object_type: Mapped[str | None] = mapped_column(String(64))
    grain: Mapped[str] = mapped_column(String(256), nullable=False)
    frequency: Mapped[str | None] = mapped_column(String(32))
    business_time_field: Mapped[str | None] = mapped_column(String(64))
    availability_rule: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    history_start: Mapped[date | None] = mapped_column(Date)
    update_mode: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="validated")
    implementation_priority: Mapped[str | None] = mapped_column(String(16))
    quality_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    retention_class: Mapped[str | None] = mapped_column(String(32))
    strategy_exposed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SourceBinding(Base):
    __tablename__ = "source_binding"
    __table_args__ = (
        UniqueConstraint("data_item_id", "source_id", "api_name", name="uq_source_binding_item_source_api"),
        {"schema": "meta"},
    )

    source_binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.data_item.data_item_id"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.data_source.source_id"), nullable=False)
    binding_code: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    api_name: Mapped[str] = mapped_column(String(128), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(64), nullable=False)
    binding_type: Mapped[str] = mapped_column(String(32), nullable=False, default="online")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="enabled")
    permission_type: Mapped[str | None] = mapped_column(String(32))
    required_points: Mapped[int | None] = mapped_column(Integer)
    entitlement_code: Mapped[str | None] = mapped_column(String(64))
    max_rows_per_request: Mapped[int | None] = mapped_column(Integer)
    max_calls_per_minute: Mapped[int | None] = mapped_column(Integer)
    max_calls_per_day: Mapped[int | None] = mapped_column(Integer)
    effective_calls_per_minute: Mapped[int | None] = mapped_column(Integer)
    history_start: Mapped[date | None] = mapped_column(Date)
    update_time_rule: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    split_dimension: Mapped[str | None] = mapped_column(String(256))
    supports_pagination: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    field_mapping_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    request_policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    capability_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    last_probe_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_probe_status: Mapped[str | None] = mapped_column(String(32))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    schema_fingerprint: Mapped[str | None] = mapped_column(String(128))
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

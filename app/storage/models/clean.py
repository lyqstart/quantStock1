import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Identity, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.models.base import Base


class CleanBatch(Base):
    __tablename__ = "clean_batch"
    __table_args__ = (
        UniqueConstraint(
            "data_item_id", "scope_key", "mapping_version", "normalization_version", "source_task_id",
            name="uq_clean_batch_source_scope_version",
        ),
        {"schema": "clean"},
    )

    clean_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clean_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.clean_run.clean_run_id"), nullable=False)
    source_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ops.collect_task.task_id"), nullable=False)
    data_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta.data_item.data_item_id"), nullable=False)
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(512), nullable=False)
    scope_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CANDIDATE")
    mapping_version: Mapped[str] = mapped_column(String(32), nullable=False)
    normalization_version: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    app_version: Mapped[str] = mapped_column(String(64), nullable=False)
    code_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    accepted_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rejected_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    candidate_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    published_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    unchanged_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    changed_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    warning_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    blocked_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    candidate_content_hash: Mapped[str | None] = mapped_column(String(128))
    published_content_hash: Mapped[str | None] = mapped_column(String(128))
    published_quality_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    current_quality_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_by_clean_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clean.clean_batch.clean_batch_id"))


class CleanBatchInput(Base):
    __tablename__ = "clean_batch_input"
    __table_args__ = (
        UniqueConstraint("clean_batch_id", "raw_batch_id", "input_role", name="uq_clean_batch_input"),
        {"schema": "clean"},
    )

    clean_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clean.clean_batch.clean_batch_id"), primary_key=True)
    raw_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("raw.raw_batch.raw_batch_id"), primary_key=True)
    input_role: Mapped[str] = mapped_column(String(16), primary_key=True, default="PRIMARY")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CleanCandidateRow(Base):
    """Internal staging rows. Published rows are copied to typed CLEAN tables only after quality passes."""

    __tablename__ = "clean_candidate_row"
    __table_args__ = (
        UniqueConstraint("clean_batch_id", "business_key_hash", name="uq_clean_candidate_business_key"),
        {"schema": "clean"},
    )

    candidate_row_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    clean_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clean.clean_batch.clean_batch_id"), nullable=False)
    raw_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("raw.raw_batch.raw_batch_id"), nullable=False)
    business_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    business_key: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CleanSkippedRow(Base):
    """RAW record intentionally excluded from canonical CLEAN, with an auditable reason."""

    __tablename__ = "clean_skipped_row"
    __table_args__ = {"schema": "clean"}

    skipped_row_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    clean_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clean.clean_batch.clean_batch_id"), nullable=False)
    raw_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("raw.raw_batch.raw_batch_id"), nullable=False)
    raw_record_id: Mapped[int | None] = mapped_column(BigInteger)
    source_record_key: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CleanTradeCalendar(Base):
    __tablename__ = "trade_calendar"
    __table_args__ = {"schema": "clean"}

    exchange_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    calendar_date: Mapped[date] = mapped_column(Date, primary_key=True)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False)
    previous_trade_date: Mapped[date | None] = mapped_column(Date)
    clean_batch_id: Mapped[uuid.UUID] = mapped_column("_clean_batch_id", UUID(as_uuid=True), ForeignKey("clean.clean_batch.clean_batch_id"), nullable=False)
    source: Mapped[str] = mapped_column("_source", String(32), nullable=False)
    available_at: Mapped[datetime] = mapped_column("_available_at", DateTime(timezone=True), nullable=False)
    quality_status: Mapped[str] = mapped_column("_quality_status", String(16), nullable=False)
    mapping_version: Mapped[str] = mapped_column("_mapping_version", String(32), nullable=False)
    normalization_version: Mapped[str] = mapped_column("_normalization_version", String(32), nullable=False)
    quality_rule_version: Mapped[str] = mapped_column("_quality_rule_version", String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column("_created_at", DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column("_updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SecurityMaster(Base):
    __tablename__ = "security_master"
    __table_args__ = {"schema": "clean"}

    security_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str | None] = mapped_column(String(128))
    area: Mapped[str | None] = mapped_column(String(64))
    industry_name: Mapped[str | None] = mapped_column(String(128))
    full_name: Mapped[str | None] = mapped_column(String(256))
    english_name: Mapped[str | None] = mapped_column(String(256))
    cn_spell: Mapped[str | None] = mapped_column(String(64))
    market: Mapped[str | None] = mapped_column(String(32))
    exchange_code: Mapped[str] = mapped_column(String(8), nullable=False)
    currency_code: Mapped[str | None] = mapped_column(String(8))
    list_status: Mapped[str] = mapped_column(String(8), nullable=False)
    list_date: Mapped[date | None] = mapped_column(Date)
    delist_date: Mapped[date | None] = mapped_column(Date)
    hsgt_status: Mapped[str | None] = mapped_column(String(8))
    actual_controller_name: Mapped[str | None] = mapped_column(String(256))
    actual_controller_entity_type: Mapped[str | None] = mapped_column(String(128))
    clean_batch_id: Mapped[uuid.UUID] = mapped_column("_clean_batch_id", UUID(as_uuid=True), ForeignKey("clean.clean_batch.clean_batch_id"), nullable=False)
    source: Mapped[str] = mapped_column("_source", String(32), nullable=False)
    available_at: Mapped[datetime] = mapped_column("_available_at", DateTime(timezone=True), nullable=False)
    quality_status: Mapped[str] = mapped_column("_quality_status", String(16), nullable=False)
    mapping_version: Mapped[str] = mapped_column("_mapping_version", String(32), nullable=False)
    normalization_version: Mapped[str] = mapped_column("_normalization_version", String(32), nullable=False)
    quality_rule_version: Mapped[str] = mapped_column("_quality_rule_version", String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column("_created_at", DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column("_updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SecurityMasterHistory(Base):
    __tablename__ = "security_master_history"
    __table_args__ = {"schema": "clean"}

    security_master_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_code: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    clean_batch_id: Mapped[uuid.UUID] = mapped_column("_clean_batch_id", UUID(as_uuid=True), ForeignKey("clean.clean_batch.clean_batch_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column("_created_at", DateTime(timezone=True), server_default=func.now(), nullable=False)


class CleanStockDaily(Base):
    __tablename__ = "stock_daily"
    __table_args__ = {"schema": "clean"}

    security_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float | None] = mapped_column(Float)
    pre_close: Mapped[float | None] = mapped_column(Float)
    change: Mapped[float | None] = mapped_column(Float)
    pct_change: Mapped[float | None] = mapped_column(Float)
    volume_share: Mapped[int | None] = mapped_column(BigInteger)
    amount_cny: Mapped[float | None] = mapped_column(Float)
    after_hours_volume_share: Mapped[int | None] = mapped_column(BigInteger)
    after_hours_amount_cny: Mapped[float | None] = mapped_column(Float)
    clean_batch_id: Mapped[uuid.UUID] = mapped_column("_clean_batch_id", UUID(as_uuid=True), ForeignKey("clean.clean_batch.clean_batch_id"), nullable=False)
    source: Mapped[str] = mapped_column("_source", String(32), nullable=False)
    available_at: Mapped[datetime] = mapped_column("_available_at", DateTime(timezone=True), nullable=False)
    quality_status: Mapped[str] = mapped_column("_quality_status", String(16), nullable=False)
    mapping_version: Mapped[str] = mapped_column("_mapping_version", String(32), nullable=False)
    normalization_version: Mapped[str] = mapped_column("_normalization_version", String(32), nullable=False)
    quality_rule_version: Mapped[str] = mapped_column("_quality_rule_version", String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column("_created_at", DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column("_updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

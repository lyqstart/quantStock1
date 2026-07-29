"""Request/response models for the unified data query API (DD-CORE-017).

Responses always carry a :class:`DataSemantics` block (REQ-CORE-026) describing
the data source, quality policy, anti-lookahead cutoff and schema/rule versions
so consumers know exactly what produced the rows.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class DataSemantics(BaseModel):
    """Metadata describing the provenance and semantics of returned rows."""

    data_source: str
    quality_policy: str
    available_at_cutoff: datetime
    schema_version: str = "v1"
    rule_version: str = "v1"
    adjustment_policy: str | None = None
    latest_available_at: datetime | None = None
    row_count: int = 0


# Backwards-compatible alias used by the design (DD-CORE-017).
DataResponseMetadata = DataSemantics


class DataResponse(BaseModel):
    rows: list[dict[str, Any]]
    metadata: DataSemantics


class DailyQueryRequest(BaseModel):
    security_codes: list[str] | None = None
    full_market: bool = False
    start_date: date | None = None
    end_date: date | None = None
    as_of_time: datetime | None = None
    adjustment: str = "none"
    quality: str = "standard"
    frequency: str = "daily"


class MinuteQueryRequest(BaseModel):
    security_codes: list[str] = Field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    frequency: str = "1min"
    as_of_time: datetime | None = None
    quality: str = "standard"


class FinancialQueryRequest(BaseModel):
    security_codes: list[str] | None = None
    full_market: bool = False
    report_type: str = "income"
    as_of_time: datetime | None = None
    revision: int | None = None
    quality: str = "standard"


class EventQueryRequest(BaseModel):
    security_codes: list[str] | None = None
    full_market: bool = False
    event_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    as_of_time: datetime | None = None
    quality: str = "standard"


class ErrorResponse(BaseModel):
    """Sanitized error body (no stacks, keys or tokens)."""

    error_code: str
    message: str

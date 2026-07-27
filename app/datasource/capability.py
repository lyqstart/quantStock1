from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.datasource.errors import ProviderRequestError
from app.datasource.tushare import TushareAdapter
from app.storage.models.meta import DataSource, SourceBinding

SHANGHAI = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class ProbeSpec:
    params: dict[str, str]
    fields: tuple[str, ...]


@dataclass(frozen=True)
class ProbeResult:
    binding_code: str
    capability_status: str
    schema_fingerprint: str | None
    response_rows: int
    error_type: str | None = None
    message: str | None = None


TRADE_CAL_FIELDS = ("exchange", "cal_date", "is_open", "pretrade_date")
STOCK_BASIC_FIELDS = ("ts_code", "symbol", "name", "list_status", "list_date", "exchange")
STOCK_DAILY_FIELDS = ("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount")


def build_probe_spec(api_name: str, *, now: datetime | None = None) -> ProbeSpec:
    current = now or datetime.now(SHANGHAI)
    if api_name == "trade_cal":
        day = current.astimezone(SHANGHAI).strftime("%Y%m%d")
        return ProbeSpec(
            params={"exchange": "SSE", "start_date": day, "end_date": day},
            fields=TRADE_CAL_FIELDS,
        )
    if api_name == "stock_basic":
        return ProbeSpec(params={"exchange": "", "list_status": "L"}, fields=STOCK_BASIC_FIELDS)
    if api_name == "daily":
        day = current.astimezone(SHANGHAI).strftime("%Y%m%d")
        return ProbeSpec(params={"trade_date": day}, fields=STOCK_DAILY_FIELDS)
    raise ValueError(f"No capability probe spec configured for api: {api_name}")


def probe_binding(
    session: Session,
    *,
    binding_code: str,
    adapter: TushareAdapter | None = None,
    now: datetime | None = None,
) -> ProbeResult:
    checked_at = now or datetime.now(SHANGHAI)
    binding = session.scalar(select(SourceBinding).where(SourceBinding.binding_code == binding_code))
    if binding is None:
        raise ValueError(f"SourceBinding not found: {binding_code}")
    if binding.adapter_type != "tushare":
        raise ValueError(f"Unsupported adapter type for probe: {binding.adapter_type}")

    source = session.get(DataSource, binding.source_id)
    active_adapter = adapter or TushareAdapter(token=get_settings().tushare_token)
    spec = build_probe_spec(binding.api_name, now=checked_at)

    try:
        result = active_adapter.query(api_name=binding.api_name, params=spec.params, fields=spec.fields)
        missing = [field for field in spec.fields if field not in result.columns]
        if missing:
            status = "schema_changed"
            binding.capability_status = status
            binding.last_probe_status = status
            binding.last_probe_at = checked_at
            binding.schema_fingerprint = result.schema_fingerprint
            if source is not None:
                source.health_status = "degraded"
                source.last_health_check_at = checked_at
            return ProbeResult(
                binding_code=binding.binding_code,
                capability_status=status,
                schema_fingerprint=result.schema_fingerprint,
                response_rows=len(result.rows),
                error_type="SCHEMA_CHANGED",
                message=f"Missing expected fields: {','.join(missing)}",
            )

        binding.capability_status = "available"
        binding.last_probe_status = "available"
        binding.last_probe_at = checked_at
        binding.schema_fingerprint = result.schema_fingerprint
        if source is not None:
            source.health_status = "healthy"
            source.last_health_check_at = checked_at
        return ProbeResult(
            binding_code=binding.binding_code,
            capability_status="available",
            schema_fingerprint=result.schema_fingerprint,
            response_rows=len(result.rows),
        )
    except ProviderRequestError as exc:
        status = _probe_status(exc.failure.error_type)
        binding.capability_status = status
        binding.last_probe_status = status
        binding.last_probe_at = checked_at
        binding.last_failure_at = checked_at
        if source is not None:
            source.health_status = "unavailable" if exc.failure.error_type == "AUTH_ERROR" else "degraded"
            source.last_health_check_at = checked_at
        return ProbeResult(
            binding_code=binding.binding_code,
            capability_status=status,
            schema_fingerprint=None,
            response_rows=0,
            error_type=exc.failure.error_type,
            message=exc.failure.message,
        )


def _probe_status(error_type: str) -> str:
    mapping = {
        "AUTH_ERROR": "temporarily_unavailable",
        "PERMISSION_DENIED": "permission_denied",
        "RATE_LIMITED": "rate_limited",
        "INVALID_REQUEST": "temporarily_unavailable",
        "NETWORK_ERROR": "temporarily_unavailable",
    }
    return mapping.get(error_type, "provider_error")

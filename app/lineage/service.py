from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models.clean import (
    CleanBatch,
    CleanBatchInput,
    CleanStockAdjFactor,
    CleanStockDaily,
    CleanStockDailyBasic,
    CleanStockLimitPrice,
    CleanStockMinute,
    CleanStockSuspendEvent,
    CleanTradeCalendar,
    SecurityMaster,
)
from app.storage.models.meta import DataItem, SourceBinding
from app.storage.models.ops import CleanRun, CollectRun, CollectTask
from app.storage.models.quality import QualityRun
from app.storage.models.raw import RawBatch


def clean_batch_lineage(session: Session, clean_batch_id: uuid.UUID) -> dict | None:
    batch = session.get(CleanBatch, clean_batch_id)
    if batch is None:
        return None
    item = session.get(DataItem, batch.data_item_id)
    clean_run = session.get(CleanRun, batch.clean_run_id)
    inputs = list(
        session.execute(
            select(CleanBatchInput, RawBatch)
            .join(RawBatch, RawBatch.raw_batch_id == CleanBatchInput.raw_batch_id)
            .where(CleanBatchInput.clean_batch_id == clean_batch_id)
            .order_by(RawBatch.created_at.asc())
        ).all()
    )
    quality_runs = list(
        session.scalars(
            select(QualityRun)
            .where(QualityRun.clean_batch_id == clean_batch_id)
            .order_by(QualityRun.started_at.asc())
        )
    )
    raw_inputs = []
    for link, raw in inputs:
        collect_run = session.get(CollectRun, raw.run_id)
        collect_task = session.get(CollectTask, collect_run.task_id) if collect_run else None
        binding = session.get(SourceBinding, raw.source_binding_id)
        raw_inputs.append(
            {
                "raw_batch_id": str(raw.raw_batch_id),
                "input_role": link.input_role,
                "row_count": raw.row_count,
                "status": raw.status,
                "source_binding": binding.binding_code if binding else None,
                "collect_run_id": str(raw.run_id),
                "collect_task_id": str(collect_task.task_id) if collect_task else None,
                "request_hash": raw.request_hash,
                "schema_version": raw.schema_version,
            }
        )
    return {
        "clean_batch_id": str(batch.clean_batch_id),
        "data_item": item.code if item else None,
        "scope_key": batch.scope_key,
        "scope": batch.scope_json,
        "status": batch.status,
        "trace_id": str(batch.trace_id),
        "mapping_version": batch.mapping_version,
        "normalization_version": batch.normalization_version,
        "quality_rule_version": batch.quality_rule_version,
        "app_version": batch.app_version,
        "code_revision": batch.code_revision,
        "clean_run": {
            "clean_run_id": str(clean_run.clean_run_id),
            "status": clean_run.status,
            "worker_id": clean_run.worker_id,
            "app_version": clean_run.app_version,
            "code_revision": clean_run.code_revision,
        } if clean_run else None,
        "quality_runs": [
            {
                "quality_run_id": str(run.quality_run_id),
                "status": run.status,
                "quality_rule_version": run.quality_rule_version,
                "issues_created": run.issues_created,
            }
            for run in quality_runs
        ],
        "raw_inputs": raw_inputs,
    }


def data_lineage(
    session: Session,
    *,
    data_item: str,
    security_code: str | None = None,
    trade_date: date | None = None,
    exchange_code: str | None = None,
    calendar_date: date | None = None,
    event_type: str | None = None,
    suspend_timing: str | None = None,
    frequency: str | None = None,
    trade_time: datetime | None = None,
) -> dict | None:
    row = None
    business_key: dict = {}
    if data_item == "stock_daily":
        if security_code is None or trade_date is None:
            raise ValueError("stock_daily requires security_code and trade_date")
        row = session.get(CleanStockDaily, {"security_code": security_code, "trade_date": trade_date})
        business_key = {"security_code": security_code, "trade_date": trade_date.isoformat()}
    elif data_item == "stock_basic":
        if security_code is None:
            raise ValueError("stock_basic requires security_code")
        row = session.get(SecurityMaster, security_code)
        business_key = {"security_code": security_code}
    elif data_item == "trade_calendar":
        if exchange_code is None or calendar_date is None:
            raise ValueError("trade_calendar requires exchange_code and calendar_date")
        row = session.get(CleanTradeCalendar, {"exchange_code": exchange_code, "calendar_date": calendar_date})
        business_key = {"exchange_code": exchange_code, "calendar_date": calendar_date.isoformat()}
    elif data_item == "stock_adj_factor":
        if security_code is None or trade_date is None:
            raise ValueError("stock_adj_factor requires security_code and trade_date")
        row = session.get(CleanStockAdjFactor, {"security_code": security_code, "trade_date": trade_date})
        business_key = {"security_code": security_code, "trade_date": trade_date.isoformat()}
    elif data_item == "stock_daily_basic":
        if security_code is None or trade_date is None:
            raise ValueError("stock_daily_basic requires security_code and trade_date")
        row = session.get(CleanStockDailyBasic, {"security_code": security_code, "trade_date": trade_date})
        business_key = {"security_code": security_code, "trade_date": trade_date.isoformat()}
    elif data_item == "stock_limit_price":
        if security_code is None or trade_date is None:
            raise ValueError("stock_limit_price requires security_code and trade_date")
        row = session.get(CleanStockLimitPrice, {"security_code": security_code, "trade_date": trade_date})
        business_key = {"security_code": security_code, "trade_date": trade_date.isoformat()}
    elif data_item == "stock_suspend":
        if security_code is None or trade_date is None or event_type is None:
            raise ValueError("stock_suspend requires security_code, trade_date and event_type")
        stmt = select(CleanStockSuspendEvent).where(
            CleanStockSuspendEvent.security_code == security_code,
            CleanStockSuspendEvent.trade_date == trade_date,
            CleanStockSuspendEvent.event_type == event_type,
        )
        if suspend_timing is None:
            stmt = stmt.where(CleanStockSuspendEvent.suspend_timing.is_(None))
        else:
            stmt = stmt.where(CleanStockSuspendEvent.suspend_timing == suspend_timing)
        row = session.scalar(stmt.limit(1))
        business_key = {
            "security_code": security_code,
            "trade_date": trade_date.isoformat(),
            "event_type": event_type,
            "suspend_timing": suspend_timing,
        }
    elif data_item == "stock_minute":
        if security_code is None or frequency is None or trade_time is None:
            raise ValueError("stock_minute requires security_code, frequency and trade_time")
        row = session.get(
            CleanStockMinute,
            {"security_code": security_code, "frequency": frequency, "trade_time": trade_time},
        )
        business_key = {
            "security_code": security_code,
            "frequency": frequency,
            "trade_time": trade_time.isoformat(),
        }
    else:
        raise ValueError(f"P4 lineage is not implemented for {data_item}")
    if row is None:
        return None
    batch_id = row.clean_batch_id
    lineage = clean_batch_lineage(session, batch_id)
    if data_item == "stock_minute":
        latest_quality = lineage["quality_runs"][-1]["status"] if lineage and lineage["quality_runs"] else None
        quality_status = {"PASSED": "PASS", "WARNED": "WARN"}.get(latest_quality, latest_quality)
    else:
        quality_status = row.quality_status
    return {"data_item": data_item, "business_key": business_key, "quality_status": quality_status, "lineage": lineage}

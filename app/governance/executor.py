from __future__ import annotations

import math
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any, Iterable

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.collect.idempotency import canonical_json, sha256_text
from app.collect.repository import ClaimedSlice, TaskRepository
from app.core.config import get_settings
from app.core.version import APP_VERSION
from app.governance.tasks import (
    MAPPING_VERSION,
    NORMALIZATION_VERSION,
    QUALITY_RULE_VERSION,
    enqueue_quality_for_clean_batch,
)
from app.storage.models.clean import (
    CleanBatch,
    CleanBatchInput,
    CleanCandidateRow,
    CleanStockDaily,
    CleanTradeCalendar,
    SecurityMaster,
    SecurityMasterHistory,
)
from app.storage.models.meta import DataItem, SourceBinding
from app.storage.models.ops import CleanRun, CollectRun, CollectTask, DataWatermark, RequestSlice
from app.storage.models.quality import QualityIssue, QualityRun
from app.storage.models.raw import RawBatch, TushareDaily, TushareStockBasic, TushareTradeCal

SECURITY_CODE = re.compile(r"^[0-9]{6}\.(SH|SZ|BJ)$")
EXCHANGE_MAP = {"SSE": "SSE", "SZSE": "SZSE", "BSE": "BSE"}
SUFFIX_EXCHANGE = {"SH": "SSE", "SZ": "SZSE", "BJ": "BSE"}
LIST_STATUSES = {"L", "D", "P", "G"}


def _date8(value: str | None) -> date | None:
    if value is None or not str(value).strip():
        return None
    return datetime.strptime(str(value), "%Y%m%d").date()


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _finite(value: float | None) -> bool:
    return value is None or math.isfinite(float(value))


def _int_exact(value: float | int | None, multiplier: int = 1) -> int | None:
    if value is None:
        return None
    converted = float(value) * multiplier
    if not math.isfinite(converted) or not converted.is_integer():
        raise ValueError("numeric value cannot be represented as an exact integer")
    return int(converted)


def _scope_payload(task: CollectTask) -> tuple[str, dict]:
    return str(task.object_scope["scope_key"]), dict(task.object_scope.get("scope") or {})


def _latest_by_key(rows: Iterable[Any], key_fn) -> list[Any]:
    latest: dict[Any, Any] = {}
    for row in rows:
        key = key_fn(row)
        previous = latest.get(key)
        if previous is None or (row.fetched_at, row.raw_id) > (previous.fetched_at, previous.raw_id):
            latest[key] = row
    return list(latest.values())


def _candidate_hash(rows: list[dict]) -> str:
    ordered = sorted(rows, key=lambda x: x["business_key_hash"])
    return sha256_text(canonical_json([{"key": x["business_key"], "payload": x["payload"]} for x in ordered]))


def _raw_batch_ids_for_task(session: Session, source_task_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(RawBatch.raw_batch_id)
            .join(CollectRun, CollectRun.run_id == RawBatch.run_id)
            .where(CollectRun.task_id == source_task_id, RawBatch.status == "SUCCEEDED")
            .order_by(RawBatch.created_at.asc())
        )
    )


def _complete_stage_task(session: Session, claimed: ClaimedSlice, task: CollectTask, *, response_rows: int) -> None:
    now = datetime.now(UTC)
    TaskRepository(session).complete_slice(
        slice_id=claimed.slice_id,
        lease_token=claimed.lease_token,
        response_rows=response_rows,
    )
    task.status = "SUCCEEDED"
    task.started_at = task.started_at or now
    task.finished_at = now
    task.last_error_type = None
    task.last_error_message = None


def prepare_stage_run(session: Session, *, claimed: ClaimedSlice, worker_id: str) -> None:
    """Persist the stage run before doing work so a real worker crash leaves LOST evidence."""
    stage = str(claimed.request_params.get("stage") or "COLLECT").upper()
    if stage not in {"CLEAN", "QUALITY"}:
        return
    task = session.get(CollectTask, claimed.task_id)
    if task is None:
        raise RuntimeError("P4 task not found while preparing stage run")
    now = datetime.now(UTC)
    task.status = "RUNNING"
    task.started_at = task.started_at or now
    if stage == "CLEAN":
        item = session.get(DataItem, task.data_item_id)
        if item is None:
            raise RuntimeError("P4 clean DataItem missing")
        existing = session.scalar(select(CleanRun).where(CleanRun.task_id == task.task_id, CleanRun.status == "RUNNING").limit(1))
        if existing is None:
            run_number = int(session.scalar(select(func.coalesce(func.max(CleanRun.run_number), 0)).where(CleanRun.task_id == task.task_id)) or 0) + 1
            session.add(CleanRun(
                task_id=task.task_id, run_number=run_number, worker_id=worker_id, trace_id=task.trace_id,
                data_item_id=item.data_item_id, status="RUNNING", mapping_version=MAPPING_VERSION,
                normalization_version=NORMALIZATION_VERSION, app_version=APP_VERSION,
                code_revision=get_settings().git_commit, started_at=now, heartbeat_at=now,
            ))
    else:
        clean_batch_id = uuid.UUID(str(claimed.request_params["source_id"]))
        existing = session.scalar(select(QualityRun).where(QualityRun.task_id == task.task_id, QualityRun.status == "RUNNING").limit(1))
        if existing is None:
            session.add(QualityRun(
                task_id=task.task_id, clean_batch_id=clean_batch_id, trace_id=task.trace_id, status="RUNNING",
                quality_rule_version=QUALITY_RULE_VERSION, app_version=APP_VERSION,
                code_revision=get_settings().git_commit, started_at=now,
            ))
    session.flush()


class CleanExecutor:
    def execute_claimed_slice(self, session: Session, *, claimed: ClaimedSlice, worker_id: str) -> None:
        task = session.get(CollectTask, claimed.task_id)
        slice_row = session.get(RequestSlice, claimed.slice_id)
        if task is None or slice_row is None:
            raise RuntimeError("P4 clean task or slice not found")
        item = session.get(DataItem, task.data_item_id)
        binding = session.get(SourceBinding, task.source_binding_id)
        if item is None or binding is None:
            raise RuntimeError("P4 clean catalog references are missing")
        source_task_id = uuid.UUID(str(slice_row.request_params["source_id"]))
        source_task = session.get(CollectTask, source_task_id)
        if source_task is None or source_task.status != "SUCCEEDED":
            raise RuntimeError("P4 clean source collection task is not SUCCEEDED")
        raw_batch_ids = _raw_batch_ids_for_task(session, source_task_id)
        if not raw_batch_ids:
            raise RuntimeError("P4 clean source task has no SUCCEEDED RawBatch")

        run = self._get_or_create_run(session, task=task, item=item, worker_id=worker_id)
        scope_key, scope_json = _scope_payload(task)
        existing_batch = session.scalar(
            select(CleanBatch).where(
                CleanBatch.data_item_id == item.data_item_id,
                CleanBatch.scope_key == scope_key,
                CleanBatch.mapping_version == MAPPING_VERSION,
                CleanBatch.normalization_version == NORMALIZATION_VERSION,
                CleanBatch.source_task_id == source_task_id,
            )
        )
        if existing_batch is not None:
            _complete_stage_task(session, claimed, task, response_rows=existing_batch.candidate_rows)
            if existing_batch.status in {"CANDIDATE", "VALIDATING"}:
                enqueue_quality_for_clean_batch(session, clean_task=task, clean_batch=existing_batch)
            run.status = "SUCCEEDED"
            run.finished_at = datetime.now(UTC)
            return

        clean_batch = CleanBatch(
            clean_run_id=run.clean_run_id,
            source_task_id=source_task_id,
            data_item_id=item.data_item_id,
            trace_id=task.trace_id,
            scope_key=scope_key,
            scope_json=scope_json,
            status="CANDIDATE",
            mapping_version=MAPPING_VERSION,
            normalization_version=NORMALIZATION_VERSION,
            quality_rule_version=QUALITY_RULE_VERSION,
            app_version=APP_VERSION,
            code_revision=get_settings().git_commit,
        )
        session.add(clean_batch)
        session.flush()
        for raw_batch_id in raw_batch_ids:
            session.add(CleanBatchInput(clean_batch_id=clean_batch.clean_batch_id, raw_batch_id=raw_batch_id, input_role="PRIMARY"))

        candidates, raw_rows, rejected_rows = self._normalize(
            session,
            item_code=item.code,
            raw_batch_ids=raw_batch_ids,
        )
        for candidate in candidates:
            session.add(
                CleanCandidateRow(
                    clean_batch_id=clean_batch.clean_batch_id,
                    raw_batch_id=candidate["raw_batch_id"],
                    business_key_hash=candidate["business_key_hash"],
                    business_key=candidate["business_key"],
                    payload=candidate["payload"],
                    source="tushare",
                )
            )

        clean_batch.raw_rows = raw_rows
        clean_batch.accepted_rows = len(candidates)
        clean_batch.rejected_rows = rejected_rows
        clean_batch.candidate_rows = len(candidates)
        clean_batch.candidate_content_hash = _candidate_hash(candidates)
        run.raw_rows = raw_rows
        run.accepted_rows = len(candidates)
        run.rejected_rows = rejected_rows
        run.status = "SUCCEEDED"
        run.finished_at = datetime.now(UTC)
        run.heartbeat_at = run.finished_at
        _complete_stage_task(session, claimed, task, response_rows=len(candidates))
        enqueue_quality_for_clean_batch(session, clean_task=task, clean_batch=clean_batch)

    @staticmethod
    def _get_or_create_run(session: Session, *, task: CollectTask, item: DataItem, worker_id: str) -> CleanRun:
        run = session.scalar(
            select(CleanRun)
            .where(CleanRun.task_id == task.task_id, CleanRun.status == "RUNNING")
            .order_by(CleanRun.run_number.desc())
            .limit(1)
        )
        now = datetime.now(UTC)
        if run is not None:
            run.heartbeat_at = now
            return run
        run_number = int(session.scalar(select(func.coalesce(func.max(CleanRun.run_number), 0)).where(CleanRun.task_id == task.task_id)) or 0) + 1
        run = CleanRun(
            task_id=task.task_id,
            run_number=run_number,
            worker_id=worker_id,
            trace_id=task.trace_id,
            data_item_id=item.data_item_id,
            status="RUNNING",
            mapping_version=MAPPING_VERSION,
            normalization_version=NORMALIZATION_VERSION,
            app_version=APP_VERSION,
            code_revision=get_settings().git_commit,
            started_at=now,
            heartbeat_at=now,
        )
        session.add(run)
        task.status = "RUNNING"
        task.started_at = task.started_at or now
        session.flush()
        return run

    def _normalize(self, session: Session, *, item_code: str, raw_batch_ids: list[uuid.UUID]) -> tuple[list[dict], int, int]:
        if item_code == "trade_calendar":
            rows = list(session.scalars(select(TushareTradeCal).where(TushareTradeCal.raw_batch_id.in_(raw_batch_ids))))
            raw_rows = len(rows)
            rows = _latest_by_key(rows, lambda r: (r.exchange, r.cal_date))
            candidates = []
            rejected = 0
            for row in rows:
                try:
                    if row.exchange not in EXCHANGE_MAP or str(row.is_open) not in {"0", "1"}:
                        raise ValueError("invalid exchange or is_open")
                    cal_date = _date8(row.cal_date)
                    if cal_date is None:
                        raise ValueError("calendar date missing")
                    payload = {
                        "exchange_code": EXCHANGE_MAP[row.exchange],
                        "calendar_date": cal_date.isoformat(),
                        "is_open": str(row.is_open) == "1",
                        "previous_trade_date": _date8(row.pretrade_date).isoformat() if _date8(row.pretrade_date) else None,
                    }
                    key = {"exchange_code": payload["exchange_code"], "calendar_date": payload["calendar_date"]}
                    candidates.append(self._candidate(row.raw_batch_id, key, payload))
                except (TypeError, ValueError):
                    rejected += 1
            return candidates, raw_rows, rejected

        if item_code == "stock_basic":
            rows = list(session.scalars(select(TushareStockBasic).where(TushareStockBasic.raw_batch_id.in_(raw_batch_ids))))
            raw_rows = len(rows)
            rows = _latest_by_key(rows, lambda r: r.ts_code)
            candidates = []
            rejected = 0
            for row in rows:
                try:
                    security_code = str(row.ts_code)
                    if not SECURITY_CODE.fullmatch(security_code):
                        raise ValueError("invalid security code")
                    exchange_code = EXCHANGE_MAP.get(str(row.exchange))
                    if exchange_code is None or SUFFIX_EXCHANGE[security_code[-2:]] != exchange_code:
                        raise ValueError("exchange mismatch")
                    status = str(row.list_status or "")
                    if status not in LIST_STATUSES:
                        raise ValueError("invalid list status")
                    payload = {
                        "security_code": security_code,
                        "symbol": str(row.symbol or security_code[:6]),
                        "name": _blank_to_none(row.name),
                        "area": _blank_to_none(row.area),
                        "industry_name": _blank_to_none(row.industry),
                        "full_name": _blank_to_none(row.fullname),
                        "english_name": _blank_to_none(row.enname),
                        "cn_spell": _blank_to_none(row.cnspell),
                        "market": _blank_to_none(row.market),
                        "exchange_code": exchange_code,
                        "currency_code": _blank_to_none(row.curr_type),
                        "list_status": status,
                        "list_date": _date8(row.list_date).isoformat() if _date8(row.list_date) else None,
                        "delist_date": _date8(row.delist_date).isoformat() if _date8(row.delist_date) else None,
                        "hsgt_status": _blank_to_none(row.is_hs),
                        "actual_controller_name": _blank_to_none(row.act_name),
                        "actual_controller_entity_type": _blank_to_none(row.act_ent_type),
                    }
                    candidates.append(self._candidate(row.raw_batch_id, {"security_code": security_code}, payload))
                except (KeyError, TypeError, ValueError):
                    rejected += 1
            return candidates, raw_rows, rejected

        if item_code == "stock_daily":
            rows = list(session.scalars(select(TushareDaily).where(TushareDaily.raw_batch_id.in_(raw_batch_ids))))
            raw_rows = len(rows)
            rows = _latest_by_key(rows, lambda r: (r.ts_code, r.trade_date))
            candidates = []
            rejected = 0
            for row in rows:
                try:
                    security_code = str(row.ts_code)
                    if not SECURITY_CODE.fullmatch(security_code):
                        raise ValueError("invalid security code")
                    trade_date = _date8(row.trade_date)
                    if trade_date is None:
                        raise ValueError("trade date missing")
                    numeric = [row.open, row.high, row.low, row.close, row.pre_close, row.change, row.pct_chg, row.vol, row.amount, row.ah_vol, row.ah_amount]
                    if not all(_finite(v) for v in numeric):
                        raise ValueError("non-finite numeric value")
                    payload = {
                        "security_code": security_code,
                        "trade_date": trade_date.isoformat(),
                        "open": row.open,
                        "high": row.high,
                        "low": row.low,
                        "close": row.close,
                        "pre_close": row.pre_close,
                        "change": row.change,
                        "pct_change": row.pct_chg,
                        "volume_share": _int_exact(row.vol, 100),
                        "amount_cny": None if row.amount is None else float(row.amount) * 1000.0,
                        "after_hours_volume_share": _int_exact(row.ah_vol, 100),
                        "after_hours_amount_cny": None if row.ah_amount is None else float(row.ah_amount) * 1000.0,
                    }
                    key = {"security_code": security_code, "trade_date": trade_date.isoformat()}
                    candidates.append(self._candidate(row.raw_batch_id, key, payload))
                except (TypeError, ValueError):
                    rejected += 1
            return candidates, raw_rows, rejected

        raise RuntimeError(f"P4 clean unsupported DataItem: {item_code}")

    @staticmethod
    def _candidate(raw_batch_id: uuid.UUID, business_key: dict, payload: dict) -> dict:
        return {
            "raw_batch_id": raw_batch_id,
            "business_key": business_key,
            "business_key_hash": sha256_text(canonical_json(business_key)),
            "payload": payload,
        }


class QualityExecutor:
    def execute_claimed_slice(self, session: Session, *, claimed: ClaimedSlice, worker_id: str) -> None:
        task = session.get(CollectTask, claimed.task_id)
        slice_row = session.get(RequestSlice, claimed.slice_id)
        if task is None or slice_row is None:
            raise RuntimeError("P4 quality task or slice not found")
        item = session.get(DataItem, task.data_item_id)
        if item is None:
            raise RuntimeError("P4 quality data item missing")
        clean_batch_id = uuid.UUID(str(slice_row.request_params["source_id"]))
        batch = session.get(CleanBatch, clean_batch_id)
        if batch is None:
            raise RuntimeError("P4 quality CleanBatch missing")

        now = datetime.now(UTC)
        run = session.scalar(
            select(QualityRun)
            .where(QualityRun.task_id == task.task_id, QualityRun.status == "RUNNING")
            .order_by(QualityRun.started_at.desc())
            .limit(1)
        )
        if run is None:
            run = QualityRun(
                task_id=task.task_id, clean_batch_id=batch.clean_batch_id, trace_id=task.trace_id,
                status="RUNNING", quality_rule_version=QUALITY_RULE_VERSION, app_version=APP_VERSION,
                code_revision=get_settings().git_commit, started_at=now,
            )
            session.add(run)
        task.status = "RUNNING"
        task.started_at = task.started_at or now
        batch.status = "VALIDATING"
        session.flush()

        candidates = list(session.scalars(select(CleanCandidateRow).where(CleanCandidateRow.clean_batch_id == batch.clean_batch_id)))
        issues = self._validate(session, item=item, batch=batch, candidates=candidates)
        for issue in issues:
            session.add(
                QualityIssue(
                    quality_run_id=run.quality_run_id,
                    data_item_id=item.data_item_id,
                    rule_code=issue["rule_code"],
                    rule_version=QUALITY_RULE_VERSION,
                    dimension=issue["dimension"],
                    severity=issue["severity"],
                    issue_type=issue["issue_type"],
                    status="OPEN",
                    scope_key=issue["scope_key"],
                    scope_json=issue.get("scope_json", {}),
                    issue_fingerprint=sha256_text(canonical_json({"item": item.code, "rule": issue["rule_code"], "scope": issue["scope_key"]})),
                    observed_value=issue.get("observed", {}),
                    expected_value=issue.get("expected", {}),
                    message=issue["message"],
                    first_seen_at=now,
                    last_seen_at=now,
                    trace_id=task.trace_id,
                )
            )

        blocked = [x for x in issues if x["severity"] == "BLOCK"]
        warned = [x for x in issues if x["severity"] == "WARN"]
        run.rules_total = max(1, len(issues) + 1)
        run.rules_blocked = len(blocked)
        run.rules_warned = len(warned)
        run.rules_passed = max(0, run.rules_total - run.rules_blocked - run.rules_warned)
        run.issues_created = len(issues)
        run.finished_at = datetime.now(UTC)
        batch.current_quality_run_id = run.quality_run_id
        batch.validated_at = run.finished_at

        if blocked:
            run.status = "BLOCKED"
            batch.status = "BLOCKED"
            batch.blocked_rows = batch.candidate_rows
            _complete_stage_task(session, claimed, task, response_rows=batch.candidate_rows)
            return

        quality_status = "WARN" if warned else "PASS"
        published, unchanged, changed = self._publish(
            session,
            item_code=item.code,
            batch=batch,
            candidates=candidates,
            quality_status=quality_status,
        )
        run.status = "WARNED" if warned else "PASSED"
        batch.status = "PUBLISHED"
        batch.published_rows = published
        batch.unchanged_rows = unchanged
        batch.changed_rows = changed
        batch.warning_rows = batch.candidate_rows if warned else 0
        batch.published_content_hash = batch.candidate_content_hash
        batch.published_quality_run_id = run.quality_run_id
        batch.current_quality_run_id = run.quality_run_id
        batch.published_at = run.finished_at
        self._supersede_previous(session, batch)
        self._update_watermark(session, item=item, task=task, batch=batch)
        session.execute(delete(CleanCandidateRow).where(CleanCandidateRow.clean_batch_id == batch.clean_batch_id))
        _complete_stage_task(session, claimed, task, response_rows=published)

    def _validate(self, session: Session, *, item: DataItem, batch: CleanBatch, candidates: list[CleanCandidateRow]) -> list[dict]:
        issues: list[dict] = []
        if batch.rejected_rows:
            issues.append(self._issue("QB-CLEAN-001", "VALIDITY", "BLOCK", "CLEAN_REJECTED_ROWS", batch.scope_key, f"{batch.rejected_rows} RAW row(s) could not be safely normalized", observed={"rejected_rows": batch.rejected_rows}, expected={"rejected_rows": 0}))
        if batch.accepted_rows != len(candidates):
            issues.append(self._issue("QB-LIN-001", "LINEAGE", "BLOCK", "CANDIDATE_COUNT_MISMATCH", batch.scope_key, "CleanBatch accepted row count does not match staged candidate rows"))
        input_count = int(session.scalar(select(func.count()).select_from(CleanBatchInput).where(CleanBatchInput.clean_batch_id == batch.clean_batch_id)) or 0)
        if input_count <= 0:
            issues.append(self._issue("QB-LIN-003", "LINEAGE", "BLOCK", "MISSING_RAW_INPUT", batch.scope_key, "CleanBatch has no RawBatch input"))

        payloads = [dict(row.payload) for row in candidates]
        if item.code == "trade_calendar":
            for payload in payloads:
                if payload["is_open"] and payload["previous_trade_date"] is not None and payload["previous_trade_date"] >= payload["calendar_date"]:
                    issues.append(self._issue("QB-CAL-004", "VALIDITY", "BLOCK", "INVALID_PREVIOUS_TRADE_DATE", canonical_json({"exchange_code": payload["exchange_code"], "calendar_date": payload["calendar_date"]}), "previous_trade_date must be earlier than calendar_date"))
                    break
            start = batch.scope_json.get("start_date")
            end = batch.scope_json.get("end_date")
            if start and end:
                expected = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
                actual_dates = {p["calendar_date"] for p in payloads}
                if len(actual_dates) != expected:
                    issues.append(self._issue("QB-CAL-003", "COMPLETENESS", "BLOCK", "CALENDAR_RANGE_GAP", batch.scope_key, "trade_calendar does not cover every natural day in requested range", observed={"distinct_dates": len(actual_dates)}, expected={"natural_days": expected}))

        elif item.code == "stock_basic":
            for payload in payloads:
                if payload["list_date"] and payload["delist_date"] and payload["list_date"] > payload["delist_date"]:
                    issues.append(self._issue("QB-STOCK-005", "VALIDITY", "BLOCK", "INVALID_LIST_DELIST_ORDER", payload["security_code"], "list_date is later than delist_date"))
                    break

        elif item.code == "stock_daily":
            day = batch.scope_json.get("trade_date")
            if day:
                calendar_open = session.scalar(
                    select(CleanTradeCalendar.is_open).where(
                        CleanTradeCalendar.exchange_code == "SSE",
                        CleanTradeCalendar.calendar_date == date.fromisoformat(day),
                    )
                )
                if calendar_open is not True:
                    issues.append(self._issue("QB-DAY-003", "CONSISTENCY", "BLOCK", "INVALID_TRADE_DATE", batch.scope_key, "stock_daily trade_date is not an open day in the published trade calendar"))
            codes = {p["security_code"] for p in payloads}
            known = set(session.scalars(select(SecurityMaster.security_code).where(SecurityMaster.security_code.in_(codes)))) if codes else set()
            unknown = sorted(codes - known)
            if unknown:
                issues.append(self._issue("QB-DAY-010", "CONSISTENCY", "BLOCK", "UNKNOWN_SECURITY", batch.scope_key, "stock_daily contains securities missing from published security_master", observed={"unknown_count": len(unknown), "sample": unknown[:10]}, expected={"unknown_count": 0}))
            for payload in payloads:
                o, h, l, c = payload["open"], payload["high"], payload["low"], payload["close"]
                if any(v is None or not math.isfinite(float(v)) for v in (o, h, l, c)):
                    issues.append(self._issue("QB-DAY-004", "VALIDITY", "BLOCK", "INVALID_OHLC", payload["security_code"], "OHLC contains NULL or non-finite values"))
                    break
                if h < max(o, l, c) or l > min(o, h, c):
                    issues.append(self._issue("QB-DAY-005", "VALIDITY", "BLOCK", "INVALID_OHLC_RELATION", payload["security_code"], "high/low relationship is invalid"))
                    break
                if payload["volume_share"] is not None and payload["volume_share"] < 0:
                    issues.append(self._issue("QB-DAY-007", "VALIDITY", "BLOCK", "NEGATIVE_VOLUME", payload["security_code"], "volume_share is negative"))
                    break
                if payload["amount_cny"] is not None and payload["amount_cny"] < 0:
                    issues.append(self._issue("QB-DAY-008", "VALIDITY", "BLOCK", "NEGATIVE_AMOUNT", payload["security_code"], "amount_cny is negative"))
                    break
        return issues

    @staticmethod
    def _issue(rule_code: str, dimension: str, severity: str, issue_type: str, scope_key: str, message: str, *, observed: dict | None = None, expected: dict | None = None) -> dict:
        return {"rule_code": rule_code, "dimension": dimension, "severity": severity, "issue_type": issue_type, "scope_key": scope_key, "message": message, "observed": observed or {}, "expected": expected or {}}

    def _publish(self, session: Session, *, item_code: str, batch: CleanBatch, candidates: list[CleanCandidateRow], quality_status: str) -> tuple[int, int, int]:
        now = datetime.now(UTC)
        common = {
            "_clean_batch_id": batch.clean_batch_id,
            "_source": "tushare",
            "_available_at": now,
            "_quality_status": quality_status,
            "_mapping_version": batch.mapping_version,
            "_normalization_version": batch.normalization_version,
            "_quality_rule_version": batch.quality_rule_version,
            "_updated_at": now,
        }
        if item_code == "trade_calendar":
            rows = [{**row.payload, "calendar_date": date.fromisoformat(row.payload["calendar_date"]), "previous_trade_date": date.fromisoformat(row.payload["previous_trade_date"]) if row.payload["previous_trade_date"] else None, **common} for row in candidates]
            return self._upsert_simple(session, CleanTradeCalendar, rows, ["exchange_code", "calendar_date"], ["is_open", "previous_trade_date"], batch)
        if item_code == "stock_basic":
            rows = []
            for row in candidates:
                payload = dict(row.payload)
                payload["list_date"] = date.fromisoformat(payload["list_date"]) if payload["list_date"] else None
                payload["delist_date"] = date.fromisoformat(payload["delist_date"]) if payload["delist_date"] else None
                rows.append({**payload, **common})
            return self._publish_security_master(session, rows=rows, batch=batch)
        if item_code == "stock_daily":
            rows = [{**row.payload, "trade_date": date.fromisoformat(row.payload["trade_date"]), **common} for row in candidates]
            business = ["open", "high", "low", "close", "pre_close", "change", "pct_change", "volume_share", "amount_cny", "after_hours_volume_share", "after_hours_amount_cny"]
            return self._upsert_simple(session, CleanStockDaily, rows, ["security_code", "trade_date"], business, batch)
        raise RuntimeError(f"P4 quality publish unsupported DataItem: {item_code}")

    @staticmethod
    def _upsert_simple(session: Session, model, rows: list[dict], key_fields: list[str], business_fields: list[str], batch: CleanBatch) -> tuple[int, int, int]:
        if not rows:
            return 0, 0, 0
        existing: dict[tuple, Any] = {}
        if model is CleanTradeCalendar:
            exchange_codes = {r["exchange_code"] for r in rows}
            dates = {r["calendar_date"] for r in rows}
            for obj in session.scalars(select(model).where(model.exchange_code.in_(exchange_codes), model.calendar_date.in_(dates))):
                existing[(obj.exchange_code, obj.calendar_date)] = obj
        elif model is CleanStockDaily:
            dates = {r["trade_date"] for r in rows}
            codes = {r["security_code"] for r in rows}
            for obj in session.scalars(select(model).where(model.trade_date.in_(dates), model.security_code.in_(codes))):
                existing[(obj.security_code, obj.trade_date)] = obj

        unchanged = 0
        changed_rows = []
        for row in rows:
            key = tuple(row[field] for field in key_fields)
            old = existing.get(key)
            if old is not None and all(getattr(old, field) == row[field] for field in business_fields):
                unchanged += 1
                continue
            changed_rows.append(row)
        if changed_rows:
            stmt = pg_insert(model).values(changed_rows)
            update_fields = {c.name: stmt.excluded[c.name] for c in model.__table__.columns if c.name not in key_fields and c.name != "_created_at"}
            session.execute(stmt.on_conflict_do_update(index_elements=key_fields, set_=update_fields))
        return len(rows), unchanged, len(changed_rows)

    @staticmethod
    def _publish_security_master(session: Session, *, rows: list[dict], batch: CleanBatch) -> tuple[int, int, int]:
        if not rows:
            return 0, 0, 0
        codes = {r["security_code"] for r in rows}
        existing = {obj.security_code: obj for obj in session.scalars(select(SecurityMaster).where(SecurityMaster.security_code.in_(codes)))}
        current_histories = {obj.security_code: obj for obj in session.scalars(select(SecurityMasterHistory).where(SecurityMasterHistory.security_code.in_(codes), SecurityMasterHistory.observed_to.is_(None)))}
        business_fields = [c.name for c in SecurityMaster.__table__.columns if not c.name.startswith("_") and c.name != "security_code"]
        unchanged = 0
        changed_rows = []
        now = datetime.now(UTC)
        for row in rows:
            old = existing.get(row["security_code"])
            if old is not None and all(getattr(old, field) == row[field] for field in business_fields):
                unchanged += 1
                continue
            changed_rows.append(row)
            payload = {field: (row[field].isoformat() if isinstance(row[field], date) else row[field]) for field in ["security_code", *business_fields]}
            content_hash = sha256_text(canonical_json(payload))
            current_history = current_histories.get(row["security_code"])
            if current_history is not None:
                current_history.observed_to = now
            session.add(SecurityMasterHistory(security_code=row["security_code"], observed_from=now, content_hash=content_hash, payload=payload, clean_batch_id=batch.clean_batch_id))
        if changed_rows:
            stmt = pg_insert(SecurityMaster).values(changed_rows)
            update_fields = {c.name: stmt.excluded[c.name] for c in SecurityMaster.__table__.columns if c.name != "security_code" and c.name != "_created_at"}
            session.execute(stmt.on_conflict_do_update(index_elements=["security_code"], set_=update_fields))
        return len(rows), unchanged, len(changed_rows)

    @staticmethod
    def _supersede_previous(session: Session, batch: CleanBatch) -> None:
        previous = list(session.scalars(select(CleanBatch).where(CleanBatch.data_item_id == batch.data_item_id, CleanBatch.scope_key == batch.scope_key, CleanBatch.status == "PUBLISHED", CleanBatch.clean_batch_id != batch.clean_batch_id)))
        now = datetime.now(UTC)
        for row in previous:
            row.status = "SUPERSEDED"
            row.superseded_at = now
            row.superseded_by_clean_batch_id = batch.clean_batch_id

    @staticmethod
    def _update_watermark(session: Session, *, item: DataItem, task: CollectTask, batch: CleanBatch) -> None:
        if item.code == "trade_calendar":
            scope_key = str(batch.scope_json.get("exchange_code", "SSE")); frequency = "day"
        elif item.code == "stock_daily":
            scope_key = "GLOBAL"; frequency = item.frequency or "day"
        else:
            scope_key = "GLOBAL"; frequency = item.frequency or ""
        watermark = session.scalar(select(DataWatermark).where(DataWatermark.data_item_id == item.data_item_id, DataWatermark.scope_key == scope_key, DataWatermark.frequency == frequency))
        if watermark is None:
            watermark = DataWatermark(data_item_id=item.data_item_id, source_binding_id=task.source_binding_id, scope_key=scope_key, frequency=frequency)
            session.add(watermark)
        watermark.latest_clean_at = batch.published_at
        watermark.latest_quality_passed_at = batch.published_at

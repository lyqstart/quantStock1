from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.collect.idempotency import build_request_hash, canonical_json, sha256_text
from app.collect.rate_limit import LocalRateLimiter
from app.collect.repository import ClaimedSlice, TaskRepository
from app.datasource.errors import ProviderRequestError
from app.datasource.tushare import TushareAdapter
from app.storage.models.meta import DataItem, SourceBinding
from app.storage.models.ops import CollectRun, CollectTask, DataWatermark, RequestSlice, SliceAttempt
from app.storage.models.raw import (
    RawBatch,
    TushareAdjFactor,
    TushareDaily,
    TushareDailyBasic,
    TushareStkLimit,
    TushareStkMins,
    TushareIncome,
    TushareFinaIndicator,
    TushareStockBasic,
    TushareSuspendD,
    TushareTradeCal,
)

TRADE_CAL_FIELDS = ("exchange", "cal_date", "is_open", "pretrade_date")
STOCK_BASIC_FIELDS = (
    "ts_code", "symbol", "name", "area", "industry", "fullname", "enname", "cnspell",
    "market", "exchange", "curr_type", "list_status", "list_date", "delist_date", "is_hs",
    "act_name", "act_ent_type",
)
STOCK_DAILY_FIELDS = (
    "ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "change", "pct_chg",
    "vol", "amount", "ah_vol", "ah_amount",
)
ADJ_FACTOR_FIELDS = ("ts_code", "trade_date", "adj_factor")
DAILY_BASIC_FIELDS = (
    "ts_code", "trade_date", "close", "turnover_rate", "turnover_rate_f", "volume_ratio",
    "pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm", "total_share",
    "float_share", "free_share", "total_mv", "circ_mv", "limit_status",
)
SUSPEND_D_FIELDS = ("ts_code", "trade_date", "suspend_timing", "suspend_type")
STK_LIMIT_FIELDS = ("trade_date", "ts_code", "pre_close", "up_limit", "down_limit")

RAW_INSERT_BATCH_SIZE = 1000

def _api_fields_from_model(model, *, exclude: set[str] | None = None) -> tuple[str, ...]:
    excluded = set(exclude or set())
    return tuple(
        column.name
        for column in model.__table__.columns
        if not column.name.startswith("_") and column.name not in excluded
    )

STK_MINS_FIELDS = _api_fields_from_model(TushareStkMins, exclude={"frequency"})
INCOME_FIELDS = _api_fields_from_model(TushareIncome)
FINA_INDICATOR_FIELDS = _api_fields_from_model(TushareFinaIndicator)


def chunk_rows(values: list[dict], size: int = RAW_INSERT_BATCH_SIZE):
    if size <= 0:
        raise ValueError("chunk size must be positive")
    for start in range(0, len(values), size):
        yield values[start : start + size]


ITEM_FIELDS = {
    "trade_calendar": TRADE_CAL_FIELDS,
    "stock_basic": STOCK_BASIC_FIELDS,
    "stock_daily": STOCK_DAILY_FIELDS,
    "stock_adj_factor": ADJ_FACTOR_FIELDS,
    "stock_daily_basic": DAILY_BASIC_FIELDS,
    "stock_suspend": SUSPEND_D_FIELDS,
    "stock_limit_price": STK_LIMIT_FIELDS,
    "stock_minute": STK_MINS_FIELDS,
    "financial_income": INCOME_FIELDS,
    "financial_indicator": FINA_INDICATOR_FIELDS,
}

ITEM_MODELS = {
    "trade_calendar": TushareTradeCal,
    "stock_basic": TushareStockBasic,
    "stock_daily": TushareDaily,
    "stock_adj_factor": TushareAdjFactor,
    "stock_daily_basic": TushareDailyBasic,
    "stock_suspend": TushareSuspendD,
    "stock_limit_price": TushareStkLimit,
    "stock_minute": TushareStkMins,
    "financial_income": TushareIncome,
    "financial_indicator": TushareFinaIndicator,
}

EXPECTED_NON_EMPTY_ITEMS = {
    "stock_daily",
    "stock_adj_factor",
    "stock_daily_basic",
    "stock_limit_price",
}

TRADE_DATE_ITEMS = EXPECTED_NON_EMPTY_ITEMS | {"stock_suspend"}


def next_offset_page_params(
    *,
    request_params: dict,
    response_rows: int,
    max_rows_per_request: int | None,
    pagination_mode: str | None,
) -> dict | None:
    if pagination_mode != "offset":
        return None
    page_size = int(request_params.get("limit") or max_rows_per_request or 0)
    if page_size <= 0:
        raise ValueError("offset pagination requires a positive page size")
    if response_rows < page_size:
        return None
    current_offset = int(request_params.get("offset") or 0)
    return {**request_params, "limit": page_size, "offset": current_offset + page_size}


def is_continuation_page(request_params: dict, pagination_mode: str | None) -> bool:
    return pagination_mode == "offset" and int(request_params.get("offset") or 0) > 0


class CollectionExecutor:
    def __init__(self, *, rate_limiter: LocalRateLimiter | None = None) -> None:
        self.rate_limiter = rate_limiter or LocalRateLimiter()

    def execute_claimed_slice(
        self,
        session: Session,
        *,
        claimed: ClaimedSlice,
        worker_id: str,
        adapter: TushareAdapter,
    ) -> None:
        slice_row = session.get(RequestSlice, claimed.slice_id)
        if slice_row is None:
            raise RuntimeError(f"RequestSlice not found: {claimed.slice_id}")
        task = session.get(CollectTask, claimed.task_id)
        if task is None:
            raise RuntimeError(f"CollectTask not found: {claimed.task_id}")
        binding = session.get(SourceBinding, task.source_binding_id)
        item = session.get(DataItem, task.data_item_id)
        if binding is None or item is None:
            raise RuntimeError("Task catalog references are missing")
        fields = ITEM_FIELDS.get(item.code)
        if fields is None:
            raise RuntimeError(f"Unsupported DataItem in collection executor: {item.code}")

        run = self._get_or_create_run(session, task=task, worker_id=worker_id)
        attempt = SliceAttempt(
            slice_id=slice_row.slice_id,
            run_id=run.run_id,
            attempt_no=slice_row.attempt_count,
            source_binding_id=binding.source_binding_id,
            request_hash=slice_row.request_hash,
            started_at=datetime.now(UTC),
            status="RUNNING",
        )
        session.add(attempt)
        session.flush()

        effective_limit = binding.effective_calls_per_minute or binding.max_calls_per_minute
        waited = self.rate_limiter.acquire(key=binding.binding_code, limit_per_minute=effective_limit)
        attempt.rate_limit_wait_ms = int(waited * 1000)

        try:
            result = adapter.query(
                api_name=binding.api_name,
                params=dict(slice_row.request_params),
                fields=fields,
            )
            missing = [field for field in fields if field not in result.columns]
            if missing:
                self._handle_provider_failure(
                    session,
                    claimed=claimed,
                    task=task,
                    run=run,
                    attempt=attempt,
                    binding=binding,
                    error_type="SCHEMA_CHANGED",
                    message=f"SCHEMA_CHANGED missing fields: {','.join(missing)}",
                    retryable=False,
                    attempt_count=slice_row.attempt_count,
                )
                return

            pagination_mode = str((binding.config or {}).get("pagination_mode", "")) or None
            next_page_params = next_offset_page_params(
                request_params=dict(slice_row.request_params),
                response_rows=len(result.rows),
                max_rows_per_request=binding.max_rows_per_request,
                pagination_mode=pagination_mode,
            )

            if (
                binding.max_rows_per_request
                and len(result.rows) >= binding.max_rows_per_request
                and pagination_mode != "offset"
            ):
                self._handle_provider_failure(
                    session,
                    claimed=claimed,
                    task=task,
                    run=run,
                    attempt=attempt,
                    binding=binding,
                    error_type="POSSIBLE_TRUNCATION",
                    message=f"response_rows={len(result.rows)} reached max_rows_per_request={binding.max_rows_per_request}",
                    retryable=False,
                    attempt_count=slice_row.attempt_count,
                )
                return

            if (
                item.code in EXPECTED_NON_EMPTY_ITEMS
                and not result.rows
                and not is_continuation_page(dict(slice_row.request_params), pagination_mode)
            ):
                self._handle_provider_failure(
                    session,
                    claimed=claimed,
                    task=task,
                    run=run,
                    attempt=attempt,
                    binding=binding,
                    error_type="SOURCE_EMPTY",
                    message=f"{item.code} returned zero rows for scheduled trading day",
                    retryable=True,
                    attempt_count=slice_row.attempt_count,
                )
                return

            self._write_rows(
                session,
                item_code=item.code,
                run=run,
                slice_row=slice_row,
                binding=binding,
                rows=result.rows,
            )
            if next_page_params is not None:
                self._ensure_next_page_slice(
                    session,
                    task=task,
                    slice_row=slice_row,
                    binding=binding,
                    request_params=next_page_params,
                )
            now = datetime.now(UTC)
            attempt.status = "SUCCEEDED"
            attempt.response_rows = len(result.rows)
            attempt.finished_at = now
            run.request_count += 1
            run.row_count += len(result.rows)
            run.heartbeat_at = now
            binding.last_success_at = now
            binding.capability_status = "available"
            binding.schema_fingerprint = result.schema_fingerprint
            TaskRepository(session).complete_slice(
                slice_id=slice_row.slice_id,
                lease_token=claimed.lease_token,
                response_rows=len(result.rows),
            )
            self._finalize_task_if_complete(session, task=task, run=run, binding=binding, item=item)
        except ProviderRequestError as exc:
            self._handle_provider_failure(
                session,
                claimed=claimed,
                task=task,
                run=run,
                attempt=attempt,
                binding=binding,
                error_type=exc.failure.error_type,
                message=exc.failure.message,
                retryable=exc.failure.retryable,
                attempt_count=slice_row.attempt_count,
            )

    @staticmethod
    def _ensure_next_page_slice(
        session: Session,
        *,
        task: CollectTask,
        slice_row: RequestSlice,
        binding: SourceBinding,
        request_params: dict,
    ) -> None:
        offset = int(request_params.get("offset") or 0)
        partition_key = f"trade_date:{request_params.get('trade_date')}:offset:{offset}"
        existing = session.scalar(
            select(RequestSlice).where(
                RequestSlice.task_id == task.task_id,
                RequestSlice.partition_key == partition_key,
            )
        )
        if existing is not None:
            return
        page_size = int(request_params.get("limit") or binding.max_rows_per_request or 1)
        session.add(
            RequestSlice(
                task_id=task.task_id,
                partition_key=partition_key,
                slice_order=max(slice_row.slice_order + 1, offset // max(page_size, 1)),
                request_params=request_params,
                request_hash=build_request_hash(
                    source_binding_code=binding.binding_code,
                    api_name=binding.api_name,
                    request_params=request_params,
                    mapping_version=binding.field_mapping_version,
                ),
                time_start=slice_row.time_start,
                time_end=slice_row.time_end,
                object_key=slice_row.object_key,
                frequency=slice_row.frequency,
                status="PENDING",
                priority=slice_row.priority,
            )
        )
        session.flush()

    @staticmethod
    def _get_or_create_run(session: Session, *, task: CollectTask, worker_id: str) -> CollectRun:
        run = session.scalar(
            select(CollectRun)
            .where(CollectRun.task_id == task.task_id, CollectRun.status == "RUNNING")
            .order_by(CollectRun.run_number.desc())
            .limit(1)
        )
        now = datetime.now(UTC)
        if run is not None:
            run.heartbeat_at = now
            return run

        max_run_number = session.scalar(
            select(func.coalesce(func.max(CollectRun.run_number), 0)).where(CollectRun.task_id == task.task_id)
        )
        run = CollectRun(
            task_id=task.task_id,
            run_number=int(max_run_number or 0) + 1,
            status="RUNNING",
            worker_id=worker_id,
            started_at=now,
            heartbeat_at=now,
        )
        session.add(run)
        task.status = "RUNNING"
        task.started_at = task.started_at or now
        session.flush()
        return run

    @staticmethod
    def _new_raw_batch(
        session: Session, *, run: CollectRun, slice_row: RequestSlice, binding: SourceBinding, row_count: int
    ) -> RawBatch:
        batch = RawBatch(
            run_id=run.run_id,
            slice_id=slice_row.slice_id,
            source_binding_id=binding.source_binding_id,
            request_hash=slice_row.request_hash,
            row_count=row_count,
            status="WRITING",
            schema_version=binding.field_mapping_version,
            started_at=datetime.now(UTC),
        )
        session.add(batch)
        session.flush()
        return batch

    @classmethod
    def _write_rows(
        cls,
        session: Session,
        *,
        item_code: str,
        run: CollectRun,
        slice_row: RequestSlice,
        binding: SourceBinding,
        rows: list[dict],
    ) -> None:
        model = ITEM_MODELS.get(item_code)
        fields = ITEM_FIELDS.get(item_code)
        if model is None or fields is None:  # pragma: no cover - guarded earlier
            raise RuntimeError(f"Unsupported DataItem writer: {item_code}")

        now = datetime.now(UTC)
        batch = cls._new_raw_batch(session, run=run, slice_row=slice_row, binding=binding, row_count=len(rows))
        values: list[dict] = []
        for row in rows:
            business = {field: row.get(field) for field in fields}
            if item_code == "trade_calendar" and business["is_open"] is not None:
                business["is_open"] = str(business["is_open"])
            if item_code == "stock_minute":
                business["frequency"] = slice_row.frequency or str(slice_row.request_params.get("freq") or "")
                if not business["frequency"]:
                    raise RuntimeError("stock_minute requires frequency in request context")
            values.append(
                {
                    "_source": "tushare",
                    "_source_api": binding.api_name,
                    "_collect_run_id": run.run_id,
                    "_raw_batch_id": batch.raw_batch_id,
                    "_fetched_at": now,
                    "_request_hash": slice_row.request_hash,
                    "_content_hash": sha256_text(canonical_json(business)),
                    "_schema_version": binding.field_mapping_version,
                    **business,
                }
            )

        if values:
            # Explicitly chunk ON CONFLICT inserts. SQLAlchemy cannot apply its normal
            # insertmanyvalues page sizing to this PostgreSQL upsert form, and a full
            # market response can exceed PostgreSQL/driver bind-parameter limits.
            for chunk in chunk_rows(values):
                stmt = pg_insert(model).values(chunk).on_conflict_do_nothing(
                    index_elements=["_source", "_source_api", "_content_hash"]
                )
                session.execute(stmt)
        batch.status = "SUCCEEDED"
        batch.finished_at = datetime.now(UTC)

    @staticmethod
    def _handle_provider_failure(
        session: Session,
        *,
        claimed: ClaimedSlice,
        task: CollectTask,
        run: CollectRun,
        attempt: SliceAttempt,
        binding: SourceBinding,
        error_type: str,
        message: str,
        retryable: bool,
        attempt_count: int,
    ) -> None:
        now = datetime.now(UTC)
        attempt.status = "FAILED"
        attempt.error_type = error_type
        attempt.error_message = message[:2000]
        attempt.finished_at = now
        run.request_count += 1
        run.error_type = error_type
        run.error_message = message[:2000]
        binding.last_failure_at = now
        task.last_error_type = error_type
        task.last_error_message = message[:2000]

        max_attempts = int((binding.config or {}).get("retry_max_attempts", 3))
        if retryable and attempt_count < max_attempts:
            delay = min(300, 2 ** max(0, attempt_count - 1))
            TaskRepository(session).release_slice_for_retry(
                slice_id=claimed.slice_id,
                lease_token=claimed.lease_token,
                error_type=error_type,
                next_retry_at=now + timedelta(seconds=delay),
            )
            return

        TaskRepository(session).fail_slice(
            slice_id=claimed.slice_id,
            lease_token=claimed.lease_token,
            error_type=error_type,
        )
        run.status = "FAILED"
        run.finished_at = now
        task.status = "FAILED"
        task.finished_at = now
        if error_type == "PERMISSION_DENIED":
            binding.capability_status = "permission_denied"
        elif error_type == "SCHEMA_CHANGED":
            binding.capability_status = "schema_changed"
        elif error_type == "AUTH_ERROR":
            binding.capability_status = "temporarily_unavailable"

    @staticmethod
    def _finalize_task_if_complete(
        session: Session,
        *,
        task: CollectTask,
        run: CollectRun,
        binding: SourceBinding,
        item: DataItem,
    ) -> None:
        remaining = session.scalar(
            select(func.count())
            .select_from(RequestSlice)
            .where(
                RequestSlice.task_id == task.task_id,
                RequestSlice.status.not_in(("SUCCEEDED", "SPLIT", "CANCELLED")),
            )
        )
        if int(remaining or 0) != 0 or not task.planning_complete:
            return

        now = datetime.now(UTC)
        task.status = "SUCCEEDED"
        task.finished_at = now
        task.last_error_type = None
        task.last_error_message = None
        run.status = "SUCCEEDED"
        run.finished_at = now
        run.heartbeat_at = now
        run.error_type = None
        run.error_message = None

        if item.code == "trade_calendar":
            scope_key, frequency, collected_at = str(task.object_scope.get("exchange", "SSE")), "day", task.time_end
        elif item.code in TRADE_DATE_ITEMS:
            scope_key, frequency, collected_at = "GLOBAL", (item.frequency or "day"), task.time_end
        elif item.code == "stock_minute":
            scope_key = str(task.object_scope.get("ts_code", "UNKNOWN"))
            frequency = task.frequency or "1min"
            collected_at = task.time_end or now
        elif item.code in {"financial_income", "financial_indicator"}:
            scope_key = str(task.object_scope.get("ts_code", "UNKNOWN"))
            frequency = item.frequency or "report"
            collected_at = task.time_end or now
        else:
            scope_key, frequency, collected_at = "GLOBAL", "", now

        watermark = session.scalar(
            select(DataWatermark).where(
                DataWatermark.data_item_id == task.data_item_id,
                DataWatermark.scope_key == scope_key,
                DataWatermark.frequency == frequency,
            )
        )
        if watermark is None:
            watermark = DataWatermark(
                data_item_id=task.data_item_id,
                source_binding_id=binding.source_binding_id,
                scope_key=scope_key,
                frequency=frequency,
            )
            session.add(watermark)
        if task.time_start is not None:
            watermark.initialized_from = task.time_start if watermark.initialized_from is None else min(watermark.initialized_from, task.time_start)
        if task.time_end is not None:
            watermark.initialized_to = task.time_end if watermark.initialized_to is None else max(watermark.initialized_to, task.time_end)
        watermark.latest_collected_at = collected_at or now
        watermark.expected_at = task.expected_business_time

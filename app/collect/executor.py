from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.collect.idempotency import canonical_json, sha256_text
from app.collect.rate_limit import LocalRateLimiter
from app.collect.repository import ClaimedSlice, TaskRepository
from app.datasource.errors import ProviderRequestError
from app.datasource.tushare import TushareAdapter
from app.storage.models.meta import DataItem, SourceBinding
from app.storage.models.ops import CollectRun, CollectTask, DataWatermark, RequestSlice, SliceAttempt
from app.storage.models.raw import RawBatch, TushareTradeCal

TRADE_CAL_FIELDS = ("exchange", "cal_date", "is_open", "pretrade_date")


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
        if item.code != "trade_calendar":
            raise RuntimeError(f"Unsupported DataItem in batch2 executor: {item.code}")

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
        waited = self.rate_limiter.acquire(
            key=binding.binding_code,
            limit_per_minute=effective_limit,
        )
        attempt.rate_limit_wait_ms = int(waited * 1000)

        try:
            result = adapter.query(
                api_name=binding.api_name,
                params=dict(slice_row.request_params),
                fields=TRADE_CAL_FIELDS,
            )
            missing = [field for field in TRADE_CAL_FIELDS if field not in result.columns]
            if missing:
                raise RuntimeError(f"SCHEMA_CHANGED missing fields: {','.join(missing)}")
            self._write_trade_calendar(
                session,
                run=run,
                slice_row=slice_row,
                binding=binding,
                rows=result.rows,
            )
            attempt.status = "SUCCEEDED"
            attempt.response_rows = len(result.rows)
            attempt.finished_at = datetime.now(UTC)
            run.request_count += 1
            run.row_count += len(result.rows)
            binding.last_success_at = datetime.now(UTC)
            binding.capability_status = "available"
            TaskRepository(session).complete_slice(
                slice_id=slice_row.slice_id,
                lease_token=claimed.lease_token,
                response_rows=len(result.rows),
            )
            self._finalize_task_if_complete(session, task=task, run=run, binding=binding)
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
        except RuntimeError as exc:
            message = str(exc)
            if message.startswith("SCHEMA_CHANGED"):
                self._handle_provider_failure(
                    session,
                    claimed=claimed,
                    task=task,
                    run=run,
                    attempt=attempt,
                    binding=binding,
                    error_type="SCHEMA_CHANGED",
                    message=message,
                    retryable=False,
                    attempt_count=slice_row.attempt_count,
                )
            else:
                raise

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
    def _write_trade_calendar(
        session: Session,
        *,
        run: CollectRun,
        slice_row: RequestSlice,
        binding: SourceBinding,
        rows: list[dict],
    ) -> None:
        now = datetime.now(UTC)
        batch = RawBatch(
            run_id=run.run_id,
            slice_id=slice_row.slice_id,
            source_binding_id=binding.source_binding_id,
            request_hash=slice_row.request_hash,
            row_count=len(rows),
            status="WRITING",
            schema_version=binding.field_mapping_version,
            started_at=now,
        )
        session.add(batch)
        session.flush()

        values = []
        for row in rows:
            business = {
                "exchange": row.get("exchange"),
                "cal_date": row.get("cal_date"),
                "is_open": str(row.get("is_open")) if row.get("is_open") is not None else None,
                "pretrade_date": row.get("pretrade_date"),
            }
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
            stmt = pg_insert(TushareTradeCal).values(values).on_conflict_do_nothing(
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
        run.status = "SUCCEEDED"
        run.finished_at = now
        run.heartbeat_at = now

        exchange = str(task.object_scope.get("exchange", "SSE"))
        existing = session.scalar(
            select(DataWatermark).where(
                DataWatermark.data_item_id == task.data_item_id,
                DataWatermark.scope_key == exchange,
                DataWatermark.frequency == "day",
            )
        )
        if existing is None:
            existing = DataWatermark(
                data_item_id=task.data_item_id,
                source_binding_id=binding.source_binding_id,
                scope_key=exchange,
                frequency="day",
            )
            session.add(existing)
        existing.initialized_from = task.time_start
        existing.initialized_to = task.time_end
        existing.latest_collected_at = task.time_end

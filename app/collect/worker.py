from __future__ import annotations

import argparse
import logging
import os
import socket
import time
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.collect.executor import CollectionExecutor
from app.collect.repository import TaskRepository
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.version import APP_VERSION
from app.datasource.tushare import TushareAdapter
from app.storage.db import get_session_factory
from app.storage.models.ops import WorkerRegistry

logger = logging.getLogger(__name__)


def _worker_id() -> str:
    return os.getenv("QUANTSTOCK1_WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"


def _register_worker(worker_id: str) -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    with get_session_factory()() as session, session.begin():
        stmt = pg_insert(WorkerRegistry).values(
            worker_id=worker_id,
            environment=settings.env,
            worker_type="collect",
            hostname=socket.gethostname(),
            process_id=os.getpid(),
            version=APP_VERSION,
            started_at=now,
            heartbeat_at=now,
            status="ONLINE",
            metadata_json={},
        ).on_conflict_do_update(
            index_elements=["worker_id"],
            set_={"heartbeat_at": now, "status": "ONLINE", "process_id": os.getpid()},
        )
        session.execute(stmt)


def run_worker(*, once: bool = False, max_slices: int | None = None) -> int:
    settings = get_settings()
    if settings.tushare_token is None or not settings.tushare_token.get_secret_value().strip():
        logger.error("QUANTSTOCK1_TUSHARE_TOKEN is not configured")
        return 2

    worker_id = _worker_id()
    _register_worker(worker_id)
    adapter = TushareAdapter(token=settings.tushare_token)
    executor = CollectionExecutor()

    processed = 0
    while True:
        with get_session_factory()() as session:
            with session.begin():
                repository = TaskRepository(session)
                recovered = repository.recover_expired_claims()
                if recovered:
                    logger.warning("Recovered %s expired worker lease(s)", recovered)
                claimed = repository.claim_next_slice(
                    worker_id=worker_id,
                    lease_seconds=settings.worker_lease_seconds,
                )
            if claimed is None:
                if once or max_slices is not None:
                    return 0
                time.sleep(settings.worker_poll_seconds)
                continue

            try:
                with session.begin():
                    executor.execute_claimed_slice(
                        session,
                        claimed=claimed,
                        worker_id=worker_id,
                        adapter=adapter,
                    )
            except Exception as exc:
                session.rollback()
                error_type = "WRITE_FAILED" if isinstance(exc, SQLAlchemyError) else "UNKNOWN_ERROR"
                original = getattr(exc, "orig", None)
                message = str(original if original is not None else exc).splitlines()[0][:1000]
                logger.error(
                    "Slice %s failed with %s: %s",
                    claimed.slice_id,
                    error_type,
                    message,
                )
                with get_session_factory()() as failure_session, failure_session.begin():
                    TaskRepository(failure_session).fail_claim_after_unhandled(
                        claimed=claimed,
                        worker_id=worker_id,
                        error_type=error_type,
                        message=message,
                    )
                if once:
                    return 1
        processed += 1
        if once or (max_slices is not None and processed >= max_slices):
            return 0


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-slices", type=int, default=None)
    args = parser.parse_args()
    raise SystemExit(run_worker(once=args.once, max_slices=args.max_slices))


if __name__ == "__main__":
    main()

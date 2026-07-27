from __future__ import annotations

import argparse
import logging
import time
from datetime import date, datetime, time as dtime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.collect.market_data_service import enqueue_stock_daily
from app.collect.scheduler_lock import release_scheduler_lock, try_acquire_scheduler_lock
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.storage.db import get_session_factory
from app.storage.models.meta import DataItem
from app.storage.models.ops import DataWatermark, TaskDefinition
from app.storage.models.raw import TushareTradeCal

logger = logging.getLogger(__name__)
SHANGHAI = ZoneInfo("Asia/Shanghai")
DEFAULT_DAILY_AVAILABLE_AFTER = dtime(16, 10)


def _open_trade_dates(session, *, after: date | None, through: date) -> list[date]:
    stmt = (
        select(TushareTradeCal.cal_date)
        .where(TushareTradeCal.is_open == "1", TushareTradeCal.cal_date <= through.strftime("%Y%m%d"))
        .distinct()
        .order_by(TushareTradeCal.cal_date.asc())
    )
    if after is not None:
        stmt = stmt.where(TushareTradeCal.cal_date > after.strftime("%Y%m%d"))
    return [datetime.strptime(value, "%Y%m%d").date() for value in session.scalars(stmt)]


def schedule_once(*, now: datetime | None = None) -> dict[str, object]:
    current = (now or datetime.now(SHANGHAI)).astimezone(SHANGHAI)
    today = current.date()

    with get_session_factory()() as session, session.begin():
        environment = get_settings().env
        if not try_acquire_scheduler_lock(session, environment):
            return {"leader": False, "created": 0, "reason": "another scheduler is leader"}
        try:
            definition = session.scalar(
                select(TaskDefinition).where(
                    TaskDefinition.task_code == "stock_daily_incremental",
                    TaskDefinition.enabled.is_(True),
                )
            )
            if definition is None:
                return {"leader": True, "created": 0, "reason": "stock_daily schedule disabled"}

            item = session.scalar(select(DataItem).where(DataItem.code == "stock_daily"))
            if item is None:
                return {"leader": True, "created": 0, "reason": "stock_daily catalog missing"}

            watermark = session.scalar(
                select(DataWatermark).where(
                    DataWatermark.data_item_id == item.data_item_id,
                    DataWatermark.scope_key == "GLOBAL",
                    DataWatermark.frequency == "day",
                )
            )
            after = watermark.latest_collected_at.astimezone(SHANGHAI).date() if watermark and watermark.latest_collected_at else None
            candidates = _open_trade_dates(session, after=after, through=today)

            # Before the first successful daily task, bootstrap only today's increment.
            if after is None:
                candidates = [day for day in candidates if day == today]

            created_ids: list[str] = []
            for business_date in candidates:
                if business_date == today and current.time() < DEFAULT_DAILY_AVAILABLE_AFTER:
                    continue
                task, created = enqueue_stock_daily(
                    session,
                    trade_date=business_date,
                    run_type="INCREMENTAL",
                    requested_by="scheduler",
                    reason="automatic daily market increment",
                )
                if created:
                    created_ids.append(str(task.task_id))

            return {
                "leader": True,
                "created": len(created_ids),
                "task_ids": created_ids,
                "through": today.strftime("%Y%m%d"),
            }
        finally:
            release_scheduler_lock(session, environment)


def run_scheduler(*, once: bool = False) -> int:
    settings = get_settings()
    while True:
        result = schedule_once()
        logger.info("scheduler scan result: %s", result)
        if once:
            return 0
        time.sleep(max(5.0, settings.scheduler_scan_seconds))


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run_scheduler(once=args.once))


if __name__ == "__main__":
    main()

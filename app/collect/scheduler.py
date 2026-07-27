from __future__ import annotations

import argparse
import logging
import time
from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.collect.market_data_service import enqueue_trade_date_item
from app.collect.scheduler_lock import release_scheduler_lock, try_acquire_scheduler_lock
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.storage.db import get_session_factory
from app.storage.models.meta import DataItem
from app.storage.models.ops import DataWatermark, TaskDefinition
from app.storage.models.raw import TushareTradeCal

logger = logging.getLogger(__name__)
SHANGHAI = ZoneInfo("Asia/Shanghai")
SUPPORTED_INCREMENTAL_ITEMS = {
    "stock_daily",
    "stock_adj_factor",
    "stock_daily_basic",
    "stock_suspend",
    "stock_limit_price",
}


def _parse_hhmm(value: str | None, default: dtime = dtime(0, 0)) -> dtime:
    if not value:
        return default
    hour, minute = value.split(":", 1)
    return dtime(int(hour), int(minute))


def _due_through_date(current: datetime, availability_rule: dict) -> date:
    delay_days = int((availability_rule or {}).get("delay_days", 0))
    return current.date() - timedelta(days=max(0, delay_days))


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


def _schedule_definition(session, *, definition: TaskDefinition, current: datetime) -> list[str]:
    item = session.get(DataItem, definition.data_item_id)
    if item is None or item.code not in SUPPORTED_INCREMENTAL_ITEMS:
        return []

    availability = dict(definition.availability_rule or {})
    due_through = _due_through_date(current, availability)
    frequency = item.frequency or "day"
    watermark = session.scalar(
        select(DataWatermark).where(
            DataWatermark.data_item_id == item.data_item_id,
            DataWatermark.scope_key == "GLOBAL",
            DataWatermark.frequency == frequency,
        )
    )
    after = watermark.latest_collected_at.astimezone(SHANGHAI).date() if watermark and watermark.latest_collected_at else None
    candidates = _open_trade_dates(session, after=after, through=due_through)

    # First bootstrap: only the latest business date that is actually due.
    if after is None and candidates:
        candidates = candidates[-1:]

    available_after = _parse_hhmm(availability.get("available_after"))
    created_ids: list[str] = []
    for business_date in candidates:
        if business_date == current.date() and current.time() < available_after:
            continue
        task, created = enqueue_trade_date_item(
            session,
            item_code=item.code,
            trade_date=business_date,
            run_type="INCREMENTAL",
            requested_by="scheduler",
            reason=f"automatic {item.code} increment",
        )
        if created:
            created_ids.append(str(task.task_id))
    return created_ids


def schedule_once(*, now: datetime | None = None) -> dict[str, object]:
    current = (now or datetime.now(SHANGHAI)).astimezone(SHANGHAI)

    with get_session_factory()() as session, session.begin():
        environment = get_settings().env
        if not try_acquire_scheduler_lock(session, environment):
            return {"leader": False, "created": 0, "reason": "another scheduler is leader"}
        try:
            definitions = list(
                session.scalars(
                    select(TaskDefinition)
                    .where(TaskDefinition.enabled.is_(True), TaskDefinition.update_mode == "trading_day")
                    .order_by(TaskDefinition.priority.asc(), TaskDefinition.task_code.asc())
                )
            )
            created_by_item: dict[str, int] = {}
            task_ids: list[str] = []
            for definition in definitions:
                item = session.get(DataItem, definition.data_item_id)
                if item is None or item.code not in SUPPORTED_INCREMENTAL_ITEMS:
                    continue
                created = _schedule_definition(session, definition=definition, current=current)
                if created:
                    created_by_item[item.code] = len(created)
                    task_ids.extend(created)

            return {
                "leader": True,
                "created": len(task_ids),
                "created_by_item": created_by_item,
                "task_ids": task_ids,
                "through": current.date().strftime("%Y%m%d"),
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

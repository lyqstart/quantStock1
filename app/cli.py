from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.collect.market_data_service import (
    enqueue_financial_item,
    enqueue_stock_basic,
    enqueue_stock_daily,
    enqueue_stock_minute,
    enqueue_trade_date_item,
)
from app.collect.scheduler import schedule_once
from app.collect.trade_calendar_service import enqueue_trade_calendar
from app.core.logging import configure_logging
from app.datasource.capability import probe_binding
from app.governance.tasks import enqueue_clean_latest
from app.storage.minute_metrics import minute_storage_report
from app.storage.db import get_session_factory

SHANGHAI = ZoneInfo("Asia/Shanghai")

TRADE_DATE_CLI_ITEMS = (
    "stock_adj_factor",
    "stock_daily_basic",
    "stock_suspend",
    "stock_limit_price",
)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)

def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=SHANGHAI)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(prog="quantstock1")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe")
    probe.add_argument("--binding", default="tushare:trade_calendar")

    trade_cal = sub.add_parser("enqueue-trade-calendar")
    trade_cal.add_argument("--start", required=True, type=_parse_date)
    trade_cal.add_argument("--end", required=True, type=_parse_date)
    trade_cal.add_argument("--exchange", default="SSE")
    trade_cal.add_argument("--run-type", default="BACKFILL", choices=["INITIALIZE", "BACKFILL", "INCREMENTAL"])
    trade_cal.add_argument("--reason", default="manual trade calendar collection")

    stock_basic = sub.add_parser("enqueue-stock-basic")
    stock_basic.add_argument("--run-type", default="INITIALIZE", choices=["INITIALIZE", "BACKFILL", "RERUN"])
    stock_basic.add_argument("--reason", default="manual stock basic collection")

    stock_daily = sub.add_parser("enqueue-stock-daily")
    stock_daily.add_argument("--date", required=True, type=_parse_date)
    stock_daily.add_argument("--run-type", default="BACKFILL", choices=["BACKFILL", "INCREMENTAL", "RERUN"])
    stock_daily.add_argument("--reason", default="manual stock daily collection")

    market_item = sub.add_parser("enqueue-market-item")
    market_item.add_argument("--item", required=True, choices=TRADE_DATE_CLI_ITEMS)
    market_item.add_argument("--date", required=True, type=_parse_date)
    market_item.add_argument("--run-type", default="BACKFILL", choices=["BACKFILL", "INCREMENTAL", "RERUN"])
    market_item.add_argument("--reason", default="manual market item collection")

    minute = sub.add_parser("enqueue-stock-minute")
    minute.add_argument("--ts-code", required=True)
    minute.add_argument("--start", required=True, type=_parse_datetime)
    minute.add_argument("--end", required=True, type=_parse_datetime)
    minute.add_argument(
        "--freq", default="1min", choices=["1min", "5min", "15min", "30min", "60min"]
    )
    minute.add_argument(
        "--run-type", default="BACKFILL", choices=["BACKFILL", "INITIALIZE", "RERUN"]
    )
    minute.add_argument("--reason", default="manual stock minute sample")

    financial = sub.add_parser("enqueue-financial-item")
    financial.add_argument(
        "--item", required=True, choices=["financial_income", "financial_indicator"]
    )
    financial.add_argument("--ts-code", required=True)
    financial.add_argument("--start", required=True, type=_parse_date)
    financial.add_argument("--end", required=True, type=_parse_date)
    financial.add_argument(
        "--run-type", default="BACKFILL", choices=["BACKFILL", "INITIALIZE", "RERUN"]
    )
    financial.add_argument("--reason", default="manual financial sample")

    clean_latest = sub.add_parser("enqueue-clean-latest")
    clean_latest.add_argument("--item", required=True, choices=["trade_calendar", "stock_basic", "stock_daily", "stock_adj_factor", "stock_daily_basic", "stock_suspend", "stock_limit_price", "stock_minute"])
    clean_latest.add_argument("--date", type=_parse_date, default=None)
    clean_latest.add_argument("--ts-code", default=None)
    clean_latest.add_argument("--freq", default=None)
    clean_latest.add_argument("--reason", default="manual P4 clean from existing RAW")

    minute_report = sub.add_parser("minute-storage-report")
    minute_report.add_argument("--date", type=_parse_date, default=None)

    sub.add_parser("scheduler-once")

    args = parser.parse_args()
    if args.command == "scheduler-once":
        print(json.dumps(schedule_once(), ensure_ascii=False, default=str))
        return

    with get_session_factory()() as session, session.begin():
        if args.command == "probe":
            result = probe_binding(session, binding_code=args.binding)
            print(json.dumps(result.__dict__, ensure_ascii=False, default=str))
            return
        if args.command == "enqueue-trade-calendar":
            task, created = enqueue_trade_calendar(
                session,
                start_date=args.start,
                end_date=args.end,
                exchange=args.exchange,
                run_type=args.run_type,
                reason=args.reason,
            )
        elif args.command == "enqueue-stock-basic":
            task, created = enqueue_stock_basic(session, run_type=args.run_type, reason=args.reason)
        elif args.command == "enqueue-stock-daily":
            task, created = enqueue_stock_daily(
                session,
                trade_date=args.date,
                run_type=args.run_type,
                requested_by="operator",
                reason=args.reason,
            )
        elif args.command == "enqueue-market-item":
            task, created = enqueue_trade_date_item(
                session,
                item_code=args.item,
                trade_date=args.date,
                run_type=args.run_type,
                requested_by="operator",
                reason=args.reason,
            )
        elif args.command == "enqueue-stock-minute":
            task, created = enqueue_stock_minute(
                session,
                ts_code=args.ts_code,
                start_time=args.start,
                end_time=args.end,
                frequency=args.freq,
                run_type=args.run_type,
                requested_by="operator",
                reason=args.reason,
            )
        elif args.command == "enqueue-financial-item":
            task, created = enqueue_financial_item(
                session,
                item_code=args.item,
                ts_code=args.ts_code,
                start_date=args.start,
                end_date=args.end,
                run_type=args.run_type,
                requested_by="operator",
                reason=args.reason,
            )
        elif args.command == "enqueue-clean-latest":
            task, created = enqueue_clean_latest(
                session,
                item_code=args.item,
                trade_date=args.date,
                security_code=args.ts_code,
                frequency=args.freq,
                requested_by="operator",
                reason=args.reason,
            )
        elif args.command == "minute-storage-report":
            print(json.dumps(minute_storage_report(session, trade_date=args.date), ensure_ascii=False, default=str))
            return
        else:  # pragma: no cover
            raise RuntimeError(f"Unhandled command: {args.command}")
        print(json.dumps({"task_id": str(task.task_id), "created": created}, ensure_ascii=False))


if __name__ == "__main__":
    main()

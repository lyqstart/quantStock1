from __future__ import annotations

import argparse
import json
from datetime import date

from app.collect.market_data_service import enqueue_stock_basic, enqueue_stock_daily
from app.collect.scheduler import schedule_once
from app.collect.trade_calendar_service import enqueue_trade_calendar
from app.core.logging import configure_logging
from app.datasource.capability import probe_binding
from app.storage.db import get_session_factory


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


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
        else:  # pragma: no cover
            raise RuntimeError(f"Unhandled command: {args.command}")
        print(json.dumps({"task_id": str(task.task_id), "created": created}, ensure_ascii=False))


if __name__ == "__main__":
    main()

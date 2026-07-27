from __future__ import annotations

import argparse
import json
from datetime import date

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

    collect = sub.add_parser("enqueue-trade-calendar")
    collect.add_argument("--start", required=True, type=_parse_date)
    collect.add_argument("--end", required=True, type=_parse_date)
    collect.add_argument("--exchange", default="SSE")
    collect.add_argument("--run-type", default="BACKFILL", choices=["INITIALIZE", "BACKFILL", "INCREMENTAL"])
    collect.add_argument("--reason", default="manual trade calendar collection")

    args = parser.parse_args()
    with get_session_factory()() as session, session.begin():
        if args.command == "probe":
            result = probe_binding(session, binding_code=args.binding)
            print(json.dumps(result.__dict__, ensure_ascii=False, default=str))
            return
        task, created = enqueue_trade_calendar(
            session,
            start_date=args.start,
            end_date=args.end,
            exchange=args.exchange,
            run_type=args.run_type,
            reason=args.reason,
        )
        print(json.dumps({"task_id": str(task.task_id), "created": created}, ensure_ascii=False))


if __name__ == "__main__":
    main()

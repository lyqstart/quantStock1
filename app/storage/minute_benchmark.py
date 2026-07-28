from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.storage.minute_metrics import minute_storage_report

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _as_int(value: Any) -> int:
    return int(value or 0)


def _bytes_per_row(size_bytes: int, rows: int) -> float | None:
    if rows <= 0:
        return None
    return round(size_bytes / rows, 6)


def _project_layer(
    layer: dict[str, Any],
    *,
    rows_per_day: int,
    trading_days: int,
) -> dict[str, Any]:
    rows = _as_int(layer.get("rows"))
    result: dict[str, Any] = {
        "observed_rows": rows,
        "projected_rows_per_day": rows_per_day,
        "projected_rows_per_year": rows_per_day * trading_days,
    }
    for key in ("table_bytes", "index_bytes", "toast_bytes", "total_bytes"):
        if key not in layer:
            continue
        observed_bytes = _as_int(layer.get(key))
        per_row = _bytes_per_row(observed_bytes, rows)
        result[f"{key}_per_row"] = per_row
        result[f"projected_{key}_per_day"] = (
            round(per_row * rows_per_day) if per_row is not None else None
        )
        result[f"projected_{key}_per_year"] = (
            round(per_row * rows_per_day * trading_days)
            if per_row is not None
            else None
        )
    return result


def _normalize_explain_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, list):
        if not payload:
            raise ValueError("EXPLAIN returned an empty JSON list")
        payload = payload[0]
    if not isinstance(payload, dict):
        raise TypeError(f"Unsupported EXPLAIN payload type: {type(payload)!r}")
    return payload


def _plan_run(payload: Any) -> dict[str, Any]:
    root = _normalize_explain_payload(payload)
    plan = root.get("Plan", {})
    return {
        "planning_time_ms": float(root.get("Planning Time", 0.0)),
        "execution_time_ms": float(root.get("Execution Time", 0.0)),
        "actual_rows": _as_int(plan.get("Actual Rows")),
        "plan_node": plan.get("Node Type"),
        "shared_hit_blocks": _as_int(plan.get("Shared Hit Blocks")),
        "shared_read_blocks": _as_int(plan.get("Shared Read Blocks")),
        "temp_read_blocks": _as_int(plan.get("Temp Read Blocks")),
        "temp_written_blocks": _as_int(plan.get("Temp Written Blocks")),
    }


def _summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        raise ValueError("At least one benchmark run is required")
    execution = [float(run["execution_time_ms"]) for run in runs]
    planning = [float(run["planning_time_ms"]) for run in runs]
    return {
        "runs": len(runs),
        "execution_time_ms": {
            "min": round(min(execution), 6),
            "median": round(median(execution), 6),
            "max": round(max(execution), 6),
        },
        "planning_time_ms": {
            "min": round(min(planning), 6),
            "median": round(median(planning), 6),
            "max": round(max(planning), 6),
        },
        "last_run": runs[-1],
    }


def _explain_analyze(
    session: Session,
    *,
    sql: str,
    params: dict[str, Any],
    repeat: int,
) -> dict[str, Any]:
    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    statement = text(
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + sql.strip()
    )
    runs = [
        _plan_run(session.execute(statement, params).scalar_one())
        for _ in range(repeat)
    ]
    return _summarize_runs(runs)


def _chunk_report(session: Session) -> dict[str, Any]:
    row = session.execute(
        text(
            """
            SELECT
              COUNT(*)::bigint AS chunks,
              COUNT(*) FILTER (WHERE is_compressed)::bigint AS compressed_chunks,
              MIN(range_start)::text AS first_range_start,
              MAX(range_end)::text AS last_range_end
            FROM timescaledb_information.chunks
            WHERE hypertable_schema='clean'
              AND hypertable_name='stock_minute'
            """
        )
    ).mappings().one()
    return {
        "chunks": _as_int(row["chunks"]),
        "compressed_chunks": _as_int(row["compressed_chunks"]),
        "first_range_start": row["first_range_start"],
        "last_range_end": row["last_range_end"],
    }


def _index_report(session: Session) -> list[dict[str, str]]:
    rows = session.execute(
        text(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname='clean'
              AND tablename='stock_minute'
            ORDER BY indexname
            """
        )
    ).mappings().all()
    return [dict(row) for row in rows]


def _storage_policy(session: Session) -> dict[str, Any] | None:
    row = session.execute(
        text(
            """
            SELECT
              policy_code,
              partition_mode,
              chunk_interval,
              compression_enabled,
              policy_version,
              notes
            FROM meta.storage_policy
            WHERE policy_code='stock_minute.clean'
              AND enabled=true
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    return dict(row) if row else None


def minute_capacity_benchmark(
    session: Session,
    *,
    trade_date: date,
    security_code: str,
    frequency: str = "1min",
    range_start: date | None = None,
    range_end: date | None = None,
    market_stocks: int = 5500,
    trading_days: int = 245,
    expected_points_per_stock: int = 241,
    repeat: int = 3,
) -> dict[str, Any]:
    if market_stocks < 1:
        raise ValueError("market_stocks must be at least 1")
    if trading_days < 1:
        raise ValueError("trading_days must be at least 1")
    if expected_points_per_stock < 1:
        raise ValueError("expected_points_per_stock must be at least 1")
    if repeat < 1:
        raise ValueError("repeat must be at least 1")

    range_start = range_start or trade_date
    range_end = range_end or trade_date
    if range_end < range_start:
        raise ValueError("range_end must not be earlier than range_start")

    day_start = datetime.combine(trade_date, time.min, tzinfo=SHANGHAI)
    day_end = day_start + timedelta(days=1)
    query_start = datetime.combine(range_start, time.min, tzinfo=SHANGHAI)
    query_end = datetime.combine(
        range_end + timedelta(days=1),
        time.min,
        tzinfo=SHANGHAI,
    )

    overall = minute_storage_report(session, trade_date=None)
    target_day = minute_storage_report(session, trade_date=trade_date)
    rows_per_day = market_stocks * expected_points_per_stock
    observed_rows = _as_int(overall["clean"]["rows"])
    observed_dates = _as_int(overall["clean"]["distinct_trade_dates"])

    minimum_rows = rows_per_day
    minimum_dates = 3
    readiness_reasons: list[str] = []
    if observed_rows < minimum_rows:
        readiness_reasons.append(
            f"observed_rows={observed_rows} is below one projected full-market day "
            f"({minimum_rows})"
        )
    if observed_dates < minimum_dates:
        readiness_reasons.append(
            f"observed_trade_dates={observed_dates} is below {minimum_dates}"
        )

    session.execute(text("SET LOCAL jit = off"))

    common = {
        "security_code": security_code,
        "frequency": frequency,
        "day_start": day_start,
        "day_end": day_end,
        "query_start": query_start,
        "query_end": query_end,
    }
    queries = {
        "single_security_day": _explain_analyze(
            session,
            sql="""
                SELECT
                  security_code,
                  frequency,
                  trade_time,
                  open,
                  high,
                  low,
                  close,
                  volume_share,
                  amount_cny
                FROM clean.stock_minute
                WHERE security_code=:security_code
                  AND frequency=:frequency
                  AND trade_time>=:day_start
                  AND trade_time<:day_end
                ORDER BY trade_time
            """,
            params=common,
            repeat=repeat,
        ),
        "market_day_grouped": _explain_analyze(
            session,
            sql="""
                SELECT
                  security_code,
                  COUNT(*) AS minute_rows,
                  MIN(trade_time) AS first_time,
                  MAX(trade_time) AS last_time,
                  SUM(volume_share) AS volume_share,
                  SUM(amount_cny) AS amount_cny
                FROM clean.stock_minute
                WHERE frequency=:frequency
                  AND trade_time>=:day_start
                  AND trade_time<:day_end
                GROUP BY security_code
                ORDER BY security_code
            """,
            params=common,
            repeat=repeat,
        ),
        "single_security_range_daily": _explain_analyze(
            session,
            sql="""
                SELECT
                  (trade_time AT TIME ZONE 'Asia/Shanghai')::date AS trade_date,
                  COUNT(*) AS minute_rows,
                  MIN(low) AS low,
                  MAX(high) AS high,
                  SUM(volume_share) AS volume_share,
                  SUM(amount_cny) AS amount_cny
                FROM clean.stock_minute
                WHERE security_code=:security_code
                  AND frequency=:frequency
                  AND trade_time>=:query_start
                  AND trade_time<:query_end
                GROUP BY (trade_time AT TIME ZONE 'Asia/Shanghai')::date
                ORDER BY trade_date
            """,
            params=common,
            repeat=repeat,
        ),
    }

    policy = _storage_policy(session)
    chunks = _chunk_report(session)
    compression_enabled = bool(policy and policy.get("compression_enabled"))
    compression_status = (
        "MEASURED"
        if chunks["compressed_chunks"] > 0
        else "NOT_MEASURED"
    )

    return {
        "benchmark_version": "minute-benchmark-v1",
        "trade_date": trade_date.isoformat(),
        "security_code": security_code,
        "frequency": frequency,
        "range": {
            "start": range_start.isoformat(),
            "end": range_end.isoformat(),
        },
        "assumptions": {
            "market_stocks": market_stocks,
            "trading_days": trading_days,
            "expected_points_per_stock": expected_points_per_stock,
            "projected_rows_per_day": rows_per_day,
        },
        "sample_readiness": {
            "status": "READY" if not readiness_reasons else "PROVISIONAL",
            "minimum_rows": minimum_rows,
            "minimum_trade_dates": minimum_dates,
            "observed_rows": observed_rows,
            "observed_trade_dates": observed_dates,
            "target_date_rows": _as_int(target_day["clean"]["rows"]),
            "target_date_coverage_ratio": round(
                _as_int(target_day["clean"]["rows"]) / rows_per_day,
                6,
            ),
            "reasons": readiness_reasons,
        },
        "storage": {
            "database_size_bytes": overall["database_size_bytes"],
            "raw": {
                **overall["raw"],
                "projection": _project_layer(
                    overall["raw"],
                    rows_per_day=rows_per_day,
                    trading_days=trading_days,
                ),
            },
            "clean": {
                **overall["clean"],
                "projection": _project_layer(
                    overall["clean"],
                    rows_per_day=rows_per_day,
                    trading_days=trading_days,
                ),
            },
            "target_date": {
                "raw_rows": target_day["raw"]["rows"],
                "clean_rows": target_day["clean"]["rows"],
            },
            "chunks": chunks,
            "indexes": _index_report(session),
            "policy": policy,
        },
        "query_performance": queries,
        "compression_evaluation": {
            "status": compression_status,
            "policy_enabled": compression_enabled,
            "compressed_chunks": chunks["compressed_chunks"],
            "decision": "DEFERRED" if compression_status != "MEASURED" else "EVIDENCE_AVAILABLE",
            "reason": (
                "No compressed chunk exists; compression remains disabled until a "
                "separate controlled benchmark is approved."
                if compression_status != "MEASURED"
                else None
            ),
        },
        "decision_guard": {
            "chunk_interval_change_allowed": False,
            "compression_enable_allowed": False,
            "full_market_history_allowed": False,
            "reason": (
                "Benchmark evidence is provisional."
                if readiness_reasons
                else "This command is evidence collection only; storage policy changes "
                "require a separate documented decision."
            ),
        },
    }

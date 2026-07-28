from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _relation_size(session: Session, relation: str) -> dict[str, int]:
    row = session.execute(
        text(
            """
            SELECT
              pg_relation_size(to_regclass(:relation))::bigint AS table_bytes,
              pg_indexes_size(to_regclass(:relation))::bigint AS index_bytes,
              pg_total_relation_size(to_regclass(:relation))::bigint AS total_bytes
            """
        ),
        {"relation": relation},
    ).mappings().one()
    return {key: int(row[key] or 0) for key in ("table_bytes", "index_bytes", "total_bytes")}


def _hypertable_size(session: Session, relation: str) -> dict[str, int]:
    row = session.execute(
        text(
            """
            SELECT
              COALESCE(SUM(table_bytes), 0)::bigint AS table_bytes,
              COALESCE(SUM(index_bytes), 0)::bigint AS index_bytes,
              COALESCE(SUM(toast_bytes), 0)::bigint AS toast_bytes,
              COALESCE(SUM(total_bytes), 0)::bigint AS total_bytes
            FROM hypertable_detailed_size(to_regclass(:relation))
            """
        ),
        {"relation": relation},
    ).mappings().one()
    return {
        key: int(row[key] or 0)
        for key in ("table_bytes", "index_bytes", "toast_bytes", "total_bytes")
    }


def _hypertable_dimension(session: Session, *, schema: str, table: str) -> dict[str, Any] | None:
    row = session.execute(
        text(
            """
            SELECT column_name, column_type::text AS column_type, time_interval::text AS time_interval
            FROM timescaledb_information.dimensions
            WHERE hypertable_schema=:schema
              AND hypertable_name=:table
              AND dimension_number=1
            """
        ),
        {"schema": schema, "table": table},
    ).mappings().first()
    return dict(row) if row else None


def minute_storage_report(session: Session, *, trade_date: date | None = None) -> dict[str, Any]:
    params = {"trade_date": trade_date}
    raw_count = int(
        session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM raw.tushare_stk_mins
                WHERE (:trade_date IS NULL OR left(trade_time, 10)::date=:trade_date)
                """
            ),
            params,
        ).scalar_one()
    )
    clean_count = int(
        session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM clean.stock_minute
                WHERE (:trade_date IS NULL OR (trade_time AT TIME ZONE 'Asia/Shanghai')::date=:trade_date)
                """
            ),
            params,
        ).scalar_one()
    )
    clean_dates = int(
        session.execute(
            text(
                """
                SELECT COUNT(DISTINCT (trade_time AT TIME ZONE 'Asia/Shanghai')::date)
                FROM clean.stock_minute
                """
            )
        ).scalar_one()
    )
    database_size = int(session.execute(text("SELECT pg_database_size(current_database())")).scalar_one())

    raw_size = _relation_size(session, "raw.tushare_stk_mins")
    dimension = _hypertable_dimension(session, schema="clean", table="stock_minute")
    clean_size = (
        _hypertable_size(session, "clean.stock_minute")
        if dimension is not None
        else _relation_size(session, "clean.stock_minute")
    )

    return {
        "trade_date": trade_date.isoformat() if trade_date else None,
        "database_size_bytes": database_size,
        "raw": {"rows": raw_count, **raw_size},
        "clean": {
            "rows": clean_count,
            "distinct_trade_dates": clean_dates,
            **clean_size,
            "hypertable": dimension is not None,
            "dimension": dimension,
        },
    }

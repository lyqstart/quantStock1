"""Financial reader for ``clean.financial_income`` / ``clean.financial_indicator``.

These multi-version CLEAN tables are created by migration 0014 (TASK-002) and
deliberately have no dedicated ORM mapping in scope, so the reader uses
parameterized SQL via :func:`sqlalchemy.text`. The table name is selected from
a fixed allow-list (no string interpolation of user input).

Mandatory behaviour:
  - by default read the ``is_current = true`` latest revision; when
    ``revision_version`` is set, read that exact historical revision
    (CP-CORE-004: time-point queries honour valid_from/available_at);
  - inject ``_available_at <= cutoff`` (anti-lookahead);
  - exclude FAILED rows (publish gate).

Only the ``clean`` schema is referenced. ``app.storage.models.raw`` is never
imported.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.datacontext.query import (
    QUALITY_STATUS_FAILED,
    QUALITY_STATUS_PASSED,
    QUALITY_STATUS_WARNING,
    QualityPolicy,
    QueryContext,
)
from app.datacontext.readers import _as_dict_list, resolve_security_codes
from app.datacontext.time_semantics import resolve_cutoff

_TABLE_BY_REPORT_TYPE: dict[str, str] = {
    "income": "clean.financial_income",
    "indicator": "clean.financial_indicator",
}


def read_financial(session: Session, query_ctx: QueryContext) -> list[dict[str, Any]]:
    """Return financial statement rows for the requested report type."""

    table = _TABLE_BY_REPORT_TYPE.get(query_ctx.report_type)
    if table is None:
        raise ValueError(f"unsupported report_type: {query_ctx.report_type!r}")

    cutoff = resolve_cutoff(
        query_ctx.time_mode,
        query_ctx.as_of_time,
        query_ctx.available_at_cutoff,
    )

    clauses: list[str] = ["_available_at <= :cutoff"]
    params: dict[str, Any] = {"cutoff": cutoff}
    clauses.append(_quality_condition(query_ctx.quality_policy))

    if query_ctx.revision_version is None:
        clauses.append("is_current = true")
    else:
        clauses.append("revision_version = :revision_version")
        params["revision_version"] = query_ctx.revision_version

    codes = resolve_security_codes(query_ctx.security_scope)
    if codes is not None:
        placeholders: list[str] = []
        for index, code in enumerate(codes):
            key = f"code_{index}"
            placeholders.append(f":{key}")
            params[key] = code
        clauses.append(f"security_code IN ({', '.join(placeholders)})")

    sql = f"SELECT * FROM {table} WHERE " + " AND ".join(clauses)
    sql += " ORDER BY security_code, report_period, revision_version"
    return _as_dict_list(session.execute(text(sql), params).mappings().all())


def _quality_condition(policy: QualityPolicy) -> str:
    if policy == QualityPolicy.STRICT:
        return f"_quality_status = '{QUALITY_STATUS_PASSED}'"
    if policy == QualityPolicy.STANDARD:
        return (
            f"_quality_status IN ('{QUALITY_STATUS_PASSED}', '{QUALITY_STATUS_WARNING}')"
        )
    # LENIENT: anything that is not FAILED.
    return f"_quality_status <> '{QUALITY_STATUS_FAILED}'"

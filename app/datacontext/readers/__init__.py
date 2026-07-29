"""DataContext readers: each reads exactly one clean-table family.

Hard constraint (REQ-CORE-016): nothing under ``app.datacontext`` may import
``app.storage.models.raw``. Readers only touch ``clean``/``meta`` schema (the
financial reader uses parameterized SQL against the ``clean`` financial tables,
which currently lack a dedicated ORM mapping).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement

from app.datacontext.query import (
    QUALITY_STATUS_FAILED,
    QualityPolicy,
    SecurityScope,
    quality_policy_allowed_statuses,
)


def build_quality_clause(
    quality_column: ColumnElement[str],
    policy: QualityPolicy,
) -> ColumnElement[bool]:
    """Build the WHERE fragment enforcing the publish gate.

    FAILED is permanently excluded for every policy (REQ-CORE-010). STRICT keeps
    only PASSED; STANDARD keeps PASSED+WARNING; LENIENT keeps anything that is
    not FAILED (so future non-terminal statuses are still admissible).
    """

    if policy == QualityPolicy.LENIENT:
        return quality_column != QUALITY_STATUS_FAILED
    return quality_column.in_(quality_policy_allowed_statuses(policy))


def resolve_security_codes(scope: SecurityScope) -> list[str] | None:
    """Return the explicit code list for single/pool scopes.

    Returns ``None`` for ``full_market`` (callers decide whether that is legal
    for their table — e.g. minute readers reject it).
    """

    if scope.is_full_market:
        return None
    return list(scope.codes) if scope.codes else None


def _as_dict_list(rows: Any) -> list[dict[str, Any]]:
    """Normalize a SQLAlchemy result into a list of plain dicts."""

    return [dict(mapping) for mapping in rows]


__all__ = [
    "read_daily",
    "read_events",
    "read_financial",
    "read_minute",
    "build_quality_clause",
    "resolve_security_codes",
]

# Submodule imports MUST come after helper definitions to avoid circular import.
from app.datacontext.readers.daily import read_daily
from app.datacontext.readers.event import read_events
from app.datacontext.readers.financial import read_financial
from app.datacontext.readers.minute import read_minute

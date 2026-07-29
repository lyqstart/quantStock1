"""Dynamic price adjustment (复权) on top of unadjusted clean values (DD-CORE-007).

Invariants (CP-CORE-003):
  - the original unadjusted ``stock_daily`` rows are NEVER mutated;
  - adjustment factors are looked up per ``(security_code, trade_date)``;
  - any factor gap (missing factor for a present row) marks that row
    ``quality_status = WARNING`` instead of fabricating a continuous price.

Adjustment math (Tushare adj_factor convention):
  adjusted_price = raw_price * (adj_factor[trade_date] / adj_factor[base])
  - FORWARD_ADJ  (前复权): base = factor of the LATEST available trade date.
  - BACKWARD_ADJ (后复权): base = factor of the EARLIEST available trade date.
"""

from __future__ import annotations

from typing import Any

from app.datacontext.query import AdjustmentMethod

# Price-like fields that get scaled by the adjustment ratio.
_PRICE_FIELDS: tuple[str, ...] = ("open", "high", "low", "close", "pre_close")


def apply_adjustment(
    rows: list[dict[str, Any]],
    adj_factors: list[dict[str, Any]],
    method: AdjustmentMethod,
) -> list[dict[str, Any]]:
    """Return a new list of adjusted rows. ``rows`` is never modified in place.

    Each input row is a dict (typically produced by a reader) carrying at least
    ``security_code``, ``trade_date`` and the OHLC price fields. Each factor row
    carries ``security_code``, ``trade_date`` and ``adj_factor``.

    When ``method == NONE`` the rows are returned as shallow copies so callers
    can freely mutate the result without touching the source.
    """

    if method == AdjustmentMethod.NONE:
        return [dict(row) for row in rows]

    factor_lookup: dict[tuple[str, Any], float] = {}
    for factor in adj_factors:
        key = (factor.get("security_code"), factor.get("trade_date"))
        value = factor.get("adj_factor")
        if value is not None:
            factor_lookup[key] = float(value)

    base_factor = _resolve_base_factor(adj_factors, method)

    adjusted: list[dict[str, Any]] = []
    for row in rows:
        new_row = dict(row)
        security_code = row.get("security_code")
        trade_date = row.get("trade_date")
        factor = factor_lookup.get((security_code, trade_date))

        if factor is None or security_code not in base_factor or base_factor[security_code] in (None, 0):
            # Factor gap: do NOT fabricate a price. Mark WARNING (CP-CORE-003).
            new_row["quality_status"] = "WARNING"
            new_row["adjustment_gap"] = True
            adjusted.append(new_row)
            continue

        ratio = factor / base_factor[security_code]
        for field_name in _PRICE_FIELDS:
            current = new_row.get(field_name)
            if current is not None:
                new_row[field_name] = current * ratio
        new_row["adjustment_method"] = method.value
        adjusted.append(new_row)

    return adjusted


def _resolve_base_factor(
    adj_factors: list[dict[str, Any]],
    method: AdjustmentMethod,
) -> dict[str, float]:
    """Per-security anchor factor used as the adjustment denominator."""

    per_security: dict[str, list[tuple[Any, float]]] = {}
    for factor in adj_factors:
        security_code = factor.get("security_code")
        value = factor.get("adj_factor")
        trade_date = factor.get("trade_date")
        if security_code is None or value is None or trade_date is None:
            continue
        per_security.setdefault(security_code, []).append((trade_date, float(value)))

    base: dict[str, float] = {}
    for security_code, entries in per_security.items():
        # Sort by trade_date to pick earliest / latest deterministically.
        entries.sort(key=lambda item: item[0])
        if method == AdjustmentMethod.BACKWARD_ADJ:
            base[security_code] = entries[0][1]
        else:  # FORWARD_ADJ
            base[security_code] = entries[-1][1]
    return base

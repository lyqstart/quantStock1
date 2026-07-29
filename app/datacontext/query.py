"""Value objects for the DataContext query layer (DD-CORE-014).

These value objects are the shared vocabulary between DataContext callers and
the per-frequency readers. They intentionally carry no ORM references so the
contract can be reused by the unified query API (DD-CORE-017).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class Frequency(str, Enum):
    """Supported bar frequencies. Minute buckets match clean.stock_minute.frequency."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MINUTE_1 = "1min"
    MINUTE_5 = "5min"
    MINUTE_15 = "15min"
    MINUTE_30 = "30min"
    MINUTE_60 = "60min"


class AdjustmentMethod(str, Enum):
    """Dynamic adjustment policies applied on top of the raw (unadjusted) values."""

    NONE = "none"          # 未复权 (return original values untouched)
    FORWARD_ADJ = "forward_adj"  # 前复权 (latest factor is the anchor)
    BACKWARD_ADJ = "backward_adj"  # 后复权 (earliest factor is the anchor)


class QualityPolicy(str, Enum):
    """Publish gate policy driving which quality_status rows are exposed."""

    STRICT = "strict"      # only PASSED rows
    STANDARD = "standard"  # PASSED + WARNING rows
    LENIENT = "lenient"    # all rows except FAILED


class TimeMode(str, Enum):
    """Anti-lookahead time semantics (DD-CORE-016 / REQ-CORE-021)."""

    RESEARCH = "research"   # latest available data (cutoff = now)
    STRATEGY = "strategy"   # user-supplied point in time
    BACKTEST = "backtest"   # strict historical replay, available_at <= as_of_time


# Quality status vocabulary (Brownfield: sourced from clean._quality_status column).
QUALITY_STATUS_PASSED = "PASSED"
QUALITY_STATUS_WARNING = "WARNING"
QUALITY_STATUS_FAILED = "FAILED"


def quality_policy_allowed_statuses(policy: QualityPolicy) -> tuple[str, ...]:
    """Return the explicit allow-list of quality statuses for a policy.

    LENIENT is handled at the clause level as ``status != FAILED`` because the
    clean layer may introduce additional non-terminal statuses; callers should
    treat the allow-list as authoritative for STRICT/STANDARD and use
    :func:`quality_policy_excludes_failed` for the LENIENT case.
    """

    if policy == QualityPolicy.STRICT:
        return (QUALITY_STATUS_PASSED,)
    if policy == QualityPolicy.STANDARD:
        return (QUALITY_STATUS_PASSED, QUALITY_STATUS_WARNING)
    # LENIENT: everything except FAILED. Represented as the full known set so the
    # caller can still build an IN-clause when it prefers allow-list semantics.
    return (QUALITY_STATUS_PASSED, QUALITY_STATUS_WARNING)


def quality_policy_excludes_failed(policy: QualityPolicy) -> bool:
    """FAILED is permanently blocked for every policy (REQ-CORE-010)."""

    return True


@dataclass(frozen=True)
class SecurityScope:
    """Which securities a query targets.

    ``mode`` is one of ``single`` / ``pool`` / ``full_market``.
    - ``single``: ``codes`` must contain exactly one code.
    - ``pool``: ``codes`` is the explicit pool membership (StockPoolVersion is a
      future-stage concern; today the caller resolves the pool to a code list).
    - ``full_market``: all securities; minute readers reject this (REQ-CORE-028).
    """

    mode: str
    codes: list[str] | None = None

    def __post_init__(self) -> None:
        if self.mode not in ("single", "pool", "full_market"):
            raise ValueError(f"unsupported security scope mode: {self.mode!r}")
        if self.mode in ("single", "pool") and not self.codes:
            raise ValueError(f"security scope mode {self.mode!r} requires non-empty codes")
        if self.mode == "single" and self.codes is not None and len(self.codes) != 1:
            raise ValueError("security scope mode 'single' requires exactly one code")

    @property
    def is_full_market(self) -> bool:
        return self.mode == "full_market"


@dataclass
class QueryContext:
    """Single query description consumed by a reader.

    Readers are responsible for calling ``resolve_cutoff`` with
    ``time_mode``/``as_of_time``/``available_at_cutoff`` to obtain the
    anti-lookahead cutoff and injecting ``available_at <= cutoff`` themselves.
    """

    security_scope: SecurityScope
    frequency: Frequency = Frequency.DAILY
    # daily / event time window (inclusive)
    start_date: date | None = None
    end_date: date | None = None
    # minute time window (inclusive)
    start_time: datetime | None = None
    end_time: datetime | None = None
    # anti-lookahead controls
    as_of_time: datetime | None = None
    available_at_cutoff: datetime | None = None
    time_mode: TimeMode = TimeMode.RESEARCH
    # post-processing policy
    adjustment_method: AdjustmentMethod = AdjustmentMethod.NONE
    quality_policy: QualityPolicy = QualityPolicy.STANDARD
    # financial reader knobs
    report_type: str = "income"          # "income" | "indicator"
    revision_version: int | None = None  # None => is_current=true (latest)
    # event reader knobs
    event_type: str | None = None
    # free-form correlation metadata (not used for filtering)
    metadata: dict[str, Any] = field(default_factory=dict)

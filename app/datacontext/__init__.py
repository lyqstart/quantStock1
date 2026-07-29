"""DataContext package (DD-CORE-014).

The P5 query layer over the CLEAN data. This module re-exports the public API
surface used by the unified query API (DD-CORE-017) and downstream research
consumers.

Import-safety contract (REQ-CORE-016): nothing in this package imports
``app.storage.models.raw``. The ``.importlinter`` configuration enforces this
statically.
"""

from app.datacontext.adjustment import apply_adjustment
from app.datacontext.alignment import align_to_calendar
from app.datacontext.context import DataContext
from app.datacontext.query import (
    AdjustmentMethod,
    Frequency,
    QualityPolicy,
    QueryContext,
    SecurityScope,
    TimeMode,
)
from app.datacontext.time_semantics import resolve_cutoff

__all__ = [
    "DataContext",
    "QueryContext",
    "SecurityScope",
    "Frequency",
    "AdjustmentMethod",
    "QualityPolicy",
    "TimeMode",
    "resolve_cutoff",
    "apply_adjustment",
    "align_to_calendar",
]

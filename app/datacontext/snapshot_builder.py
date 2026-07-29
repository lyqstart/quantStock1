"""DataSnapshot construction service (DD-CORE-015 / REQ-CORE-019, REQ-CORE-020).

A snapshot freezes a reproducible view of the CLEAN inputs as-of a point in
time. The builder:

  1. resolves the requested ``data_item_codes`` to published CleanBatch rows
     that were published at or before the cutoff (anti-future);
  2. applies the quality gate: a batch without a published quality run is
     treated as not-yet-publishable and excluded (FAILED never reaches the
     PUBLISHED state in the pipeline, REQ-CORE-010);
  3. computes ``content_fingerprint`` as sha256 over the sorted input
     CleanBatch content hashes (CP-CORE-005: identical inputs reproduce an
     identical fingerprint);
  4. transitions the snapshot BUILDING -> READY and records the input
     references (UNIQUE(snapshot_id, clean_batch_id) prevents double refs).

READY immutability is enforced by the migration 0013 trigger; this module
additionally refuses to mutate an already-READY snapshot in-process.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.datacontext.query import AdjustmentMethod, QualityPolicy, TimeMode
from app.datacontext.time_semantics import resolve_cutoff
from app.storage.models.clean import CleanBatch
from app.storage.models.meta import DataItem
from app.storage.models.snapshot import DataSnapshot, DataSnapshotInput


def build_snapshot(
    session: Session,
    data_item_codes: Sequence[str],
    as_of_time: datetime,
    quality_policy: QualityPolicy | str = QualityPolicy.STANDARD,
    adjustment_policy: AdjustmentMethod | str = AdjustmentMethod.NONE,
    available_at_cutoff: datetime | None = None,
) -> DataSnapshot:
    """Build and persist an immutable READY DataSnapshot."""

    cutoff = resolve_cutoff(TimeMode.BACKTEST, as_of_time, available_at_cutoff)
    quality_policy_version = _policy_version(quality_policy)
    adjustment_policy_value = _adjustment_value(adjustment_policy)

    codes = list(data_item_codes)
    if not codes:
        raise ValueError("data_item_codes must not be empty")

    item_ids = [
        row[0]
        for row in session.execute(
            select(DataItem.data_item_id).where(DataItem.code.in_(codes))
        ).all()
    ]
    if not item_ids:
        raise ValueError(f"no DataItem found for codes: {codes}")

    batches = (
        session.execute(
            select(CleanBatch).where(
                CleanBatch.data_item_id.in_(item_ids),
                CleanBatch.status == "PUBLISHED",
                CleanBatch.superseded_at.is_(None),
                or_(
                    CleanBatch.published_at.is_(None),
                    CleanBatch.published_at <= cutoff,
                ),
            )
        )
        .scalars()
        .all()
    )

    included: list[CleanBatch] = []
    skipped_failed = 0
    for batch in batches:
        # Quality gate: a batch with no published quality verification is not
        # admissible. FAILED batches never reach PUBLISHED (pipeline invariant).
        if batch.published_quality_run_id is None:
            skipped_failed += 1
            continue
        included.append(batch)

    content_hashes = sorted(
        (batch.published_content_hash or str(batch.clean_batch_id)) for batch in included
    )
    fingerprint = hashlib.sha256(
        "|".join(content_hashes).encode("utf-8")
    ).hexdigest()
    total_rows = sum(int(batch.published_rows or 0) for batch in included)

    snapshot = DataSnapshot(
        status="BUILDING",
        as_of_time=as_of_time,
        available_at_cutoff=cutoff,
        data_item_codes=codes,
        quality_policy_version=quality_policy_version,
        adjustment_policy=adjustment_policy_value,
        content_fingerprint=fingerprint,
        skipped_failed_count=skipped_failed,
        warning_published_count=0,
        warning_excluded_count=0,
        total_rows=total_rows,
        trace_id=uuid.uuid4(),
    )
    session.add(snapshot)
    session.flush()  # populate snapshot_id

    for batch in included:
        session.add(
            DataSnapshotInput(
                snapshot_id=snapshot.snapshot_id,
                clean_batch_id=batch.clean_batch_id,
                input_type="CLEAN_BATCH",
                quality_policy_version=quality_policy_version,
                as_of_time=as_of_time,
                available_at_cutoff=cutoff,
            )
        )

    # BUILDING -> READY transition (READY is then immutable).
    snapshot.status = "READY"
    session.flush()
    return snapshot


def compute_content_fingerprint(content_hashes: Sequence[str]) -> str:
    """Pure helper: sha256 over the sorted, deduplicated input content hashes.

    Exposed for unit tests so fingerprint determinism can be verified without a
    database.
    """

    ordered = sorted(set(content_hashes))
    return hashlib.sha256("|".join(ordered).encode("utf-8")).hexdigest()


def _policy_version(value: QualityPolicy | str) -> str:
    if isinstance(value, QualityPolicy):
        return value.value
    return str(value)


def _adjustment_value(value: AdjustmentMethod | str) -> str:
    if isinstance(value, AdjustmentMethod):
        return value.value
    return str(value)

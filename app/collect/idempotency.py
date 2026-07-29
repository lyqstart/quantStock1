import hashlib
import json
from datetime import date, datetime
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_normalize(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_task_idempotency_key(
    *,
    data_item_code: str,
    source_binding_code: str,
    run_type: str,
    object_scope: dict[str, Any],
    time_start: datetime | date | None = None,
    time_end: datetime | date | None = None,
    frequency: str | None = None,
) -> str:
    payload = {
        "data_item": data_item_code,
        "source_binding": source_binding_code,
        "run_type": run_type,
        "object_scope": object_scope,
        "time_start": time_start,
        "time_end": time_end,
        "frequency": frequency,
    }
    return sha256_text(canonical_json(payload))


def build_request_hash(*, source_binding_code: str, api_name: str, request_params: dict[str, Any], mapping_version: str) -> str:
    return sha256_text(canonical_json({
        "source_binding": source_binding_code,
        "api_name": api_name,
        "request_params": request_params,
        "mapping_version": mapping_version,
    }))


class ForceRerunRequired(Exception):
    """Raised when a completed idempotency key is re-submitted without force_rerun=True (DD-CORE-004)."""


def check_idempotency_or_force(
    *,
    existing_completed: bool,
    force_rerun: bool = False,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    """Decide whether a task may proceed or must generate a new Run (REQ-CORE-004).

    - If no prior completed run exists → proceed normally (``{"action": "proceed"}``).
    - If a prior completed run exists and ``force_rerun=True`` → caller must create
      a **new** CollectRun with a new idempotency key suffix
      (``{"action": "new_run", "reason": "force_rerun"}``).
    - If a prior completed run exists and ``force_rerun=False`` → reject
      (raise :class:`ForceRerunRequired`).
    """
    if not existing_completed:
        return {"action": "proceed"}

    if force_rerun:
        return {"action": "new_run", "reason": "force_rerun", "original_key": idempotency_key}

    raise ForceRerunRequired(
        f"idempotency key '{idempotency_key}' already completed; "
        "pass force_rerun=True to generate a new Run"
    )

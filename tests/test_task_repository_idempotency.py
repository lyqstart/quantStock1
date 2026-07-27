from __future__ import annotations

from contextlib import nullcontext

from app.collect.repository import TaskRepository
from app.storage.models.ops import CollectTask


class ExistingTaskSession:
    def __init__(self, existing: CollectTask) -> None:
        self.existing = existing
        self.begin_nested_called = False

    def scalar(self, _statement):
        return self.existing

    def begin_nested(self):
        self.begin_nested_called = True
        return nullcontext()


def test_duplicate_task_is_returned_without_reinserting() -> None:
    existing = CollectTask(
        data_item_id=None,
        source_binding_id=None,
        run_type="INCREMENTAL",
        object_scope={"type": "market"},
        status="PENDING",
        idempotency_key="same-key",
        idempotency_version=1,
    )
    duplicate = CollectTask(
        data_item_id=None,
        source_binding_id=None,
        run_type="INCREMENTAL",
        object_scope={"type": "market"},
        status="PENDING",
        idempotency_key="same-key",
        idempotency_version=1,
    )
    session = ExistingTaskSession(existing)

    persisted, created = TaskRepository(session).create_task_idempotent(duplicate)

    assert persisted is existing
    assert created is False
    assert session.begin_nested_called is False

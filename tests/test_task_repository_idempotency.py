from __future__ import annotations

import uuid

from sqlalchemy.dialects import postgresql

from app.collect.repository import TaskRepository
from app.storage.models.ops import CollectTask


class DuplicateTaskSession:
    def __init__(self, existing: CollectTask) -> None:
        self.existing = existing
        self.statements = []
        self.scalar_calls = 0

    def scalar(self, statement):
        self.statements.append(statement)
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            # PostgreSQL INSERT ... ON CONFLICT DO NOTHING returned no row.
            return None
        return self.existing

    def get(self, _model, _key):
        raise AssertionError("get() must not be used for a duplicate task")


class InsertedTaskSession:
    def __init__(self, persisted: CollectTask) -> None:
        self.persisted = persisted
        self.statements = []

    def scalar(self, statement):
        self.statements.append(statement)
        return self.persisted.task_id

    def get(self, _model, key):
        assert key == self.persisted.task_id
        return self.persisted


def _task(key: str, *, explicit_version: bool = True) -> CollectTask:
    kwargs = dict(
        task_id=uuid.uuid4(),
        data_item_id=uuid.uuid4(),
        source_binding_id=uuid.uuid4(),
        run_type="INCREMENTAL",
        object_scope={"type": "market"},
        status="PENDING",
        idempotency_key=key,
    )
    if explicit_version:
        kwargs["idempotency_version"] = 1
    return CollectTask(**kwargs)


def test_duplicate_task_uses_postgres_on_conflict_and_returns_existing() -> None:
    existing = _task("same-key")
    duplicate = _task("same-key")
    session = DuplicateTaskSession(existing)

    persisted, created = TaskRepository(session).create_task_idempotent(duplicate)

    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT ON CONSTRAINT uq_collect_task_idempotency DO NOTHING" in sql
    assert persisted is existing
    assert created is False


def test_new_task_is_returned_after_atomic_insert() -> None:
    persisted = _task("new-key")
    candidate = _task("new-key")
    persisted.task_id = candidate.task_id
    session = InsertedTaskSession(persisted)

    result, created = TaskRepository(session).create_task_idempotent(candidate)

    assert result is persisted
    assert created is True


def test_duplicate_task_uses_effective_default_idempotency_version() -> None:
    existing = _task("same-key")
    duplicate = _task("same-key", explicit_version=False)
    assert duplicate.idempotency_version is None
    session = DuplicateTaskSession(existing)

    persisted, created = TaskRepository(session).create_task_idempotent(duplicate)

    insert_compiled = session.statements[0].compile(dialect=postgresql.dialect())
    lookup_compiled = session.statements[1].compile(dialect=postgresql.dialect())
    assert insert_compiled.params["idempotency_version"] == 1
    assert 1 in lookup_compiled.params.values()
    assert "same-key" in lookup_compiled.params.values()
    assert persisted is existing
    assert created is False

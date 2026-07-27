from types import SimpleNamespace
from uuid import uuid4

from app.collect.repository import ClaimedSlice, TaskRepository
from app.storage.models.clean import CleanBatch
from app.storage.models.ops import CollectTask


class _FakeSession:
    def __init__(self, *, scalars, objects):
        self._scalars = iter(scalars)
        self._objects = objects
        self.flushed = False

    def scalar(self, _statement):
        return next(self._scalars)

    def get(self, model, key):
        return self._objects.get((model, key))

    def flush(self):
        self.flushed = True


def _claimed(task_id, slice_id, lease_token):
    return ClaimedSlice(
        slice_id=slice_id,
        task_id=task_id,
        lease_token=lease_token,
        request_params={},
        request_hash="hash",
    )


def test_unhandled_clean_error_closes_persisted_clean_run() -> None:
    task_id, slice_id, lease_token = uuid4(), uuid4(), uuid4()
    slice_row = SimpleNamespace(
        status="RUNNING",
        last_error_type=None,
        next_retry_at=None,
        leased_by="worker-1",
        leased_at=object(),
        lease_expires_at=object(),
        lease_token=lease_token,
    )
    task = SimpleNamespace(
        task_id=task_id,
        object_scope={"stage": "CLEAN"},
        status="RUNNING",
        finished_at=None,
        last_error_type=None,
        last_error_message=None,
    )
    clean_run = SimpleNamespace(
        status="RUNNING", finished_at=None, error_type=None, error_message=None
    )
    session = _FakeSession(
        scalars=[slice_row, clean_run],
        objects={(CollectTask, task_id): task},
    )

    TaskRepository(session).fail_claim_after_unhandled(
        claimed=_claimed(task_id, slice_id, lease_token),
        worker_id="worker-1",
        error_type="UNKNOWN_ERROR",
        message="clean failed",
    )

    assert task.status == "FAILED"
    assert clean_run.status == "FAILED"
    assert clean_run.error_type == "UNKNOWN_ERROR"
    assert slice_row.status == "FAILED"
    assert session.flushed is True


def test_unhandled_quality_error_returns_batch_to_candidate() -> None:
    task_id, slice_id, lease_token, batch_id = uuid4(), uuid4(), uuid4(), uuid4()
    run_id = uuid4()
    slice_row = SimpleNamespace(
        status="RUNNING",
        last_error_type=None,
        next_retry_at=None,
        leased_by="worker-1",
        leased_at=object(),
        lease_expires_at=object(),
        lease_token=lease_token,
    )
    task = SimpleNamespace(
        task_id=task_id,
        object_scope={"stage": "QUALITY"},
        status="RUNNING",
        finished_at=None,
        last_error_type=None,
        last_error_message=None,
    )
    quality_run = SimpleNamespace(
        quality_run_id=run_id,
        clean_batch_id=batch_id,
        status="RUNNING",
        finished_at=None,
    )
    batch = SimpleNamespace(status="VALIDATING", current_quality_run_id=None)
    session = _FakeSession(
        scalars=[slice_row, quality_run],
        objects={(CollectTask, task_id): task, (CleanBatch, batch_id): batch},
    )

    TaskRepository(session).fail_claim_after_unhandled(
        claimed=_claimed(task_id, slice_id, lease_token),
        worker_id="worker-1",
        error_type="WRITE_FAILED",
        message="quality failed",
    )

    assert task.status == "FAILED"
    assert quality_run.status == "FAILED"
    assert batch.status == "CANDIDATE"
    assert batch.current_quality_run_id == run_id
    assert slice_row.status == "FAILED"
    assert session.flushed is True

from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.governance import tasks


class _ScalarSequenceSession:
    def __init__(self, values):
        self._values = iter(values)

    def scalar(self, _statement):
        return next(self._values)


def _source_task(item_id: uuid.UUID):
    return SimpleNamespace(
        task_id=uuid.uuid4(),
        data_item_id=item_id,
        status="SUCCEEDED",
        time_start=datetime(2026, 7, 27, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )


def test_enqueue_clean_latest_queues_new_quality_for_old_blocked_batch(monkeypatch):
    item_id = uuid.uuid4()
    item = SimpleNamespace(data_item_id=item_id, code="stock_limit_price")
    source_task = _source_task(item_id)
    clean_task = SimpleNamespace(task_id=uuid.uuid4(), status="SUCCEEDED")
    batch = SimpleNamespace(
        clean_batch_id=uuid.uuid4(),
        status="BLOCKED",
        quality_rule_version="quality-v2",
    )
    session = _ScalarSequenceSession([item, source_task, batch])
    calls = []

    monkeypatch.setattr(
        tasks,
        "enqueue_clean_for_collect_task",
        lambda *args, **kwargs: (clean_task, False),
    )
    monkeypatch.setattr(
        tasks,
        "enqueue_quality_for_clean_batch",
        lambda *args, **kwargs: calls.append(kwargs) or (SimpleNamespace(), True),
    )

    result = tasks.enqueue_clean_latest(
        session,
        item_code="stock_limit_price",
        trade_date=datetime(2026, 7, 27).date(),
    )

    assert result == (clean_task, False)
    assert len(calls) == 1
    assert calls[0]["clean_batch"] is batch
    assert "quality-v4" in calls[0]["reason"]


def test_enqueue_clean_latest_does_not_repeat_same_quality_version(monkeypatch):
    item_id = uuid.uuid4()
    item = SimpleNamespace(data_item_id=item_id, code="stock_limit_price")
    source_task = _source_task(item_id)
    clean_task = SimpleNamespace(task_id=uuid.uuid4(), status="SUCCEEDED")
    batch = SimpleNamespace(
        clean_batch_id=uuid.uuid4(),
        status="BLOCKED",
        quality_rule_version=tasks.QUALITY_RULE_VERSION,
    )
    session = _ScalarSequenceSession([item, source_task, batch])
    calls = []

    monkeypatch.setattr(
        tasks,
        "enqueue_clean_for_collect_task",
        lambda *args, **kwargs: (clean_task, False),
    )
    monkeypatch.setattr(
        tasks,
        "enqueue_quality_for_clean_batch",
        lambda *args, **kwargs: calls.append(kwargs) or (SimpleNamespace(), True),
    )

    tasks.enqueue_clean_latest(
        session,
        item_code="stock_limit_price",
        trade_date=datetime(2026, 7, 27).date(),
    )

    assert calls == []

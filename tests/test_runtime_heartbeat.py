from pathlib import Path


def test_worker_persists_heartbeats() -> None:
    source = Path("app/collect/worker.py").read_text(encoding="utf-8")
    assert "_heartbeat_worker(worker_id)" in source
    assert 'status="OFFLINE"' in source


def test_scheduler_persists_state() -> None:
    source = Path("app/collect/scheduler.py").read_text(encoding="utf-8")
    assert "_record_scheduler_state" in source
    assert 'status="LEADER"' in source
    assert 'status="OFFLINE"' in source

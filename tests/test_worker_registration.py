from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.storage.models.ops import WorkerRegistry


def test_worker_registry_uses_safe_python_attribute_for_metadata_column() -> None:
    assert WorkerRegistry.metadata_json.property.columns[0].name == "metadata"
    stmt = pg_insert(WorkerRegistry).values(
        worker_id="worker-1",
        environment="test",
        worker_type="collect",
        hostname="host",
        process_id=1,
        version="test",
        started_at="2026-07-27T00:00:00+00:00",
        heartbeat_at="2026-07-27T00:00:00+00:00",
        status="ONLINE",
        metadata_json={},
    )
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "metadata" in compiled

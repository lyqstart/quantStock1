from app.storage.models import Base


def test_audit_event_is_part_of_metadata() -> None:
    assert "audit.audit_event" in Base.metadata.tables

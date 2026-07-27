from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_does_not_require_database() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_has_environment() -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["environment"] in {"dev", "test", "prod"}

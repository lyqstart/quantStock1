from app.main import app


def test_ops_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}
    expected = {
        "/api/v1/ops/overview",
        "/api/v1/ops/data-items",
        "/api/v1/ops/tasks",
        "/api/v1/ops/tasks/{task_id}",
        "/api/v1/ops/backfills",
        "/api/v1/ops/tasks/{task_id}/retry",
        "/api/v1/ops/tasks/{task_id}/pause",
        "/api/v1/ops/tasks/{task_id}/resume",
        "/api/v1/ops/tasks/{task_id}/cancel",
        "/api/v1/ops/workers",
        "/api/v1/ops/scheduler",
    }
    assert expected.issubset(paths)

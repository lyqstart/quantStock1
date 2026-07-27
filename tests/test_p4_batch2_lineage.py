import inspect

from app.lineage.service import data_lineage
from app.main import app


def test_p4_batch2_lineage_accepts_suspend_event_identity() -> None:
    params = inspect.signature(data_lineage).parameters
    assert "event_type" in params
    assert "suspend_timing" in params


def test_lineage_route_exposes_suspend_event_query_parameters() -> None:
    operation = app.openapi()["paths"]["/api/v1/lineage/data/{data_item}"]["get"]
    names = {param["name"] for param in operation["parameters"]}
    assert {"event_type", "suspend_timing"} <= names

import inspect

from app.lineage.service import data_lineage
from app.main import app


def test_minute_lineage_accepts_full_business_identity() -> None:
    params = inspect.signature(data_lineage).parameters
    assert {"security_code", "frequency", "trade_time"} <= set(params)


def test_lineage_route_exposes_minute_identity_query_parameters() -> None:
    operation = app.openapi()["paths"]["/api/v1/lineage/data/{data_item}"]["get"]
    names = {param["name"] for param in operation["parameters"]}
    assert {"security_code", "frequency", "trade_time"} <= names

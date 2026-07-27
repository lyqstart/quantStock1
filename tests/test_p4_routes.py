from app.main import app


def test_p4_lineage_routes_are_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/v1/lineage/clean-batches/{clean_batch_id}" in paths
    assert "/api/v1/lineage/data/{data_item}" in paths

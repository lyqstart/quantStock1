from app.collect.planners.stock_basic import LIST_STATUSES, plan_stock_basic_slices


def test_stock_basic_collects_all_lifecycle_statuses() -> None:
    plans = plan_stock_basic_slices(source_binding_code="tushare:stock_basic", mapping_version="v1")
    assert tuple(plan.request_params["list_status"] for plan in plans) == LIST_STATUSES
    assert len({plan.partition_key for plan in plans}) == len(LIST_STATUSES)

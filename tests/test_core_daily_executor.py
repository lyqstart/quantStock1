from app.collect.executor import EXPECTED_NON_EMPTY_ITEMS, ITEM_FIELDS, ITEM_MODELS


def test_four_core_daily_items_are_registered_in_executor() -> None:
    items = {"stock_adj_factor", "stock_daily_basic", "stock_suspend", "stock_limit_price"}
    assert items <= ITEM_FIELDS.keys()
    assert items <= ITEM_MODELS.keys()
    assert "stock_suspend" not in EXPECTED_NON_EMPTY_ITEMS
    assert {"stock_adj_factor", "stock_daily_basic", "stock_limit_price"} <= EXPECTED_NON_EMPTY_ITEMS

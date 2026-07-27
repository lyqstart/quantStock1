from app.collect.executor import (
    EXPECTED_NON_EMPTY_ITEMS,
    ITEM_FIELDS,
    ITEM_MODELS,
    is_continuation_page,
    next_offset_page_params,
)


def test_four_core_daily_items_are_registered_in_executor() -> None:
    items = {"stock_adj_factor", "stock_daily_basic", "stock_suspend", "stock_limit_price"}
    assert items <= ITEM_FIELDS.keys()
    assert items <= ITEM_MODELS.keys()
    assert "stock_suspend" not in EXPECTED_NON_EMPTY_ITEMS
    assert {"stock_adj_factor", "stock_daily_basic", "stock_limit_price"} <= EXPECTED_NON_EMPTY_ITEMS


def test_offset_pagination_continues_when_page_hits_limit() -> None:
    params = {"trade_date": "20260727", "limit": 5800, "offset": 0}
    assert next_offset_page_params(
        request_params=params,
        response_rows=5800,
        max_rows_per_request=5800,
        pagination_mode="offset",
    ) == {"trade_date": "20260727", "limit": 5800, "offset": 5800}


def test_offset_pagination_stops_on_short_page_and_allows_empty_continuation() -> None:
    params = {"trade_date": "20260727", "limit": 5800, "offset": 5800}
    assert next_offset_page_params(
        request_params=params,
        response_rows=125,
        max_rows_per_request=5800,
        pagination_mode="offset",
    ) is None
    assert is_continuation_page(params, "offset") is True

"""E2E test configuration for the 10 DataItem × 8 stage matrix (DD-CORE-021)."""

import pytest

from tests.conftest import skip_no_pg

DATA_ITEMS = [
    "trade_calendar",
    "stock_basic",
    "stock_daily",
    "stock_adj_factor",
    "stock_daily_basic",
    "stock_suspend",
    "stock_limit_price",
    "stock_minute",
    "financial_income",
    "financial_indicator",
]

PIPELINE_STAGES = [
    "collect",
    "raw",
    "clean",
    "quality",
    "lineage",
    "snapshot",
    "datacontext",
    "api",
]


def pytest_generate_tests(metafunc):
    if "data_item" in metafunc.fixturenames and "stage" in metafunc.fixturenames:
        metafunc.parametrize("data_item", DATA_ITEMS)
        metafunc.parametrize("stage", PIPELINE_STAGES)

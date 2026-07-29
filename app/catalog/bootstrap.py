from dataclasses import dataclass


@dataclass(frozen=True)
class InitialDataItem:
    code: str
    name: str
    domain: str
    grain: str
    frequency: str | None
    api_name: str
    critical: bool = False
    permission_type: str = "points"
    max_rows_per_request: int | None = None


INITIAL_DATA_ITEMS = (
    InitialDataItem("trade_calendar", "交易日历", "D01", "交易所+日期", "day", "trade_cal", True),
    InitialDataItem("stock_basic", "股票基础信息", "D01", "股票", None, "stock_basic", True, max_rows_per_request=6000),
    InitialDataItem("stock_daily", "A股日线", "D02", "股票+交易日", "day", "daily", True, max_rows_per_request=6000),
    InitialDataItem("stock_adj_factor", "复权因子", "D02", "股票+交易日", "day", "adj_factor", True),
    InitialDataItem("stock_daily_basic", "每日指标", "D02", "股票+交易日", "day", "daily_basic", True, max_rows_per_request=6000),
    InitialDataItem("stock_suspend", "停复牌", "D02", "股票+日期+状态", "event", "suspend_d"),
    InitialDataItem("stock_limit_price", "涨跌停价格", "D02", "股票+交易日", "day", "stk_limit", max_rows_per_request=5800),
    InitialDataItem("stock_minute", "A股历史分钟", "D03", "股票+频率+交易时间", "minute", "stk_mins", permission_type="entitlement", max_rows_per_request=8000),
    InitialDataItem("financial_income", "利润表", "D05", "股票+报告期+版本", "report", "income"),
    InitialDataItem("financial_indicator", "财务指标", "D05", "股票+报告期+版本", "report", "fina_indicator", max_rows_per_request=100),
)


class DataItemMetadataError(Exception):
    """Raised when a DataItem lacks required metadata (DD-CORE-001)."""

    ERROR_CODE = "DATAITEM_METADATA_INCOMPLETE"

    def __init__(self, code: str, missing_fields: list[str]) -> None:
        self.code = code
        self.missing_fields = missing_fields
        super().__init__(
            f"{self.ERROR_CODE}: DataItem '{code}' missing required fields: {missing_fields}"
        )


_REQUIRED_METADATA_FIELDS = (
    "business_time_field",
    "update_mode",
    "frequency",
    "retention_class",
    "quality_policy_ref",
)


def validate_dataitem_metadata(item) -> None:
    """Reject a DataItem from entering ACTIVE if any required metadata field is empty (REQ-CORE-001).

    ``item`` is an ORM DataItem or InitialDataItem-like object with attributes.
    Raises :class:`DataItemMetadataError` with ``ERROR_CODE = DATAITEM_METADATA_INCOMPLETE``
    listing the missing fields.
    """
    missing = [
        field
        for field in _REQUIRED_METADATA_FIELDS
        if not getattr(item, field, None)
    ]
    if missing:
        raise DataItemMetadataError(getattr(item, "code", "<unknown>"), missing)

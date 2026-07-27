from pydantic import SecretStr

from app.datasource.errors import ProviderRequestError
from app.datasource.tushare import TushareAdapter


class FakeFrame:
    columns = ["exchange", "cal_date", "is_open", "pretrade_date"]

    def to_dict(self, orient: str):
        assert orient == "records"
        return [{"exchange": "SSE", "cal_date": "20260727", "is_open": 1, "pretrade_date": "20260724"}]


class FakeClient:
    def query(self, api_name: str, **kwargs):
        assert api_name == "trade_cal"
        assert kwargs["exchange"] == "SSE"
        assert "fields" in kwargs
        return FakeFrame()


class FailingClient:
    def query(self, api_name: str, **kwargs):
        raise RuntimeError("您的token abc-secret 无权限访问该接口")


def test_tushare_adapter_returns_records_and_schema_fingerprint() -> None:
    adapter = TushareAdapter(client=FakeClient())
    result = adapter.query(
        api_name="trade_cal",
        params={"exchange": "SSE"},
        fields=("exchange", "cal_date", "is_open", "pretrade_date"),
    )
    assert result.rows[0]["cal_date"] == "20260727"
    assert result.columns[0] == "exchange"
    assert len(result.schema_fingerprint) == 64


def test_tushare_adapter_classifies_permission_and_redacts_token() -> None:
    adapter = TushareAdapter(token=SecretStr("abc-secret"), client=FailingClient())
    try:
        adapter.query(api_name="trade_cal")
    except ProviderRequestError as exc:
        assert exc.failure.error_type == "PERMISSION_DENIED"
        assert exc.failure.retryable is False
        assert "abc-secret" not in exc.failure.message
    else:
        raise AssertionError("ProviderRequestError was not raised")

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import SecretStr

from app.datasource.errors import ProviderRequestError, classify_provider_exception


class DataFrameLike(Protocol):
    @property
    def columns(self) -> Any: ...

    def to_dict(self, orient: str) -> list[dict[str, Any]]: ...


class TushareClientLike(Protocol):
    def query(self, api_name: str, **kwargs: Any) -> DataFrameLike: ...


@dataclass(frozen=True)
class ProviderResult:
    rows: list[dict[str, Any]]
    columns: tuple[str, ...]
    schema_fingerprint: str


class TushareAdapter:
    def __init__(self, *, token: SecretStr | None = None, client: TushareClientLike | None = None) -> None:
        if client is None and token is None:
            raise ValueError("Tushare token is required when no client is injected")
        self._token = token
        self._client = client or self._build_client(token)

    @staticmethod
    def _build_client(token: SecretStr | None) -> TushareClientLike:
        if token is None:
            raise ValueError("Tushare token is required")
        try:
            import tushare as ts
        except ImportError as exc:  # pragma: no cover - runtime dependency guard
            raise RuntimeError("tushare package is not installed") from exc
        return ts.pro_api(token.get_secret_value())

    def query(
        self,
        *,
        api_name: str,
        params: dict[str, Any] | None = None,
        fields: tuple[str, ...] | None = None,
    ) -> ProviderResult:
        request_params = dict(params or {})
        if fields:
            request_params["fields"] = ",".join(fields)
        try:
            frame = self._client.query(api_name, **request_params)
        except Exception as exc:  # provider SDK exposes heterogeneous exception classes
            secrets: tuple[str, ...] = ()
            if self._token is not None:
                secrets = (self._token.get_secret_value(),)
            raise ProviderRequestError(classify_provider_exception(exc, secret_values=secrets)) from exc

        columns = tuple(str(column) for column in frame.columns)
        rows = frame.to_dict("records")
        return ProviderResult(
            rows=[{str(k): _normalize_scalar(v) for k, v in row.items()} for row in rows],
            columns=columns,
            schema_fingerprint=_schema_fingerprint(columns),
        )


def _schema_fingerprint(columns: tuple[str, ...]) -> str:
    return hashlib.sha256("\x1f".join(columns).encode("utf-8")).hexdigest()


def _normalize_scalar(value: Any) -> Any:
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except (ImportError, TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass
    return value

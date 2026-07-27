from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderFailure:
    error_type: str
    message: str
    retryable: bool


class ProviderRequestError(RuntimeError):
    def __init__(self, failure: ProviderFailure) -> None:
        super().__init__(failure.message)
        self.failure = failure


def classify_provider_exception(exc: Exception, *, secret_values: tuple[str, ...] = ()) -> ProviderFailure:
    raw = str(exc) or exc.__class__.__name__
    message = raw
    for secret in secret_values:
        if secret:
            message = message.replace(secret, "***")

    lowered = message.lower()
    class_name = exc.__class__.__name__.lower()

    if any(token in lowered for token in ("无权限", "权限", "积分不足", "permission denied", "not allowed")):
        return ProviderFailure("PERMISSION_DENIED", message, False)
    if any(token in lowered for token in ("频次", "每分钟", "访问太频繁", "rate limit", "too many requests")):
        return ProviderFailure("RATE_LIMITED", message, True)
    if any(token in lowered for token in ("token", "凭证", "认证", "authentication", "unauthorized")):
        return ProviderFailure("AUTH_ERROR", message, False)
    if any(token in lowered for token in ("参数", "parameter", "invalid request", "必须输入")):
        return ProviderFailure("INVALID_REQUEST", message, False)
    if any(token in class_name for token in ("timeout", "connection", "network")) or any(
        token in lowered for token in ("timeout", "timed out", "connection reset", "connection aborted", "网络")
    ):
        return ProviderFailure("NETWORK_ERROR", message, True)
    return ProviderFailure("PROVIDER_ERROR", message, True)

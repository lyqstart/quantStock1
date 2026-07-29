from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="QUANTSTOCK1_",
        case_sensitive=False,
        extra="ignore",
    )

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+psycopg://quantstock1:change_me@localhost:5432/quantstock1"
    tushare_token: SecretStr | None = None
    log_level: str = "INFO"
    git_commit: str = "unknown"
    build_time: str = "unknown"
    worker_poll_seconds: float = 2.0
    worker_lease_seconds: int = 60
    scheduler_scan_seconds: float = 60.0
    worker_lost_threshold_seconds: int = 600
    recovery_sla_seconds: int = 900
    query_timeout_seconds: int = 30


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

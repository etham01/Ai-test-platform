from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEFAULT_DATABASE_URL = (
    "mysql+pymysql://smarttest:smarttest_dev_pw@127.0.0.1:3307/smarttest?charset=utf8mb4"
)
DEFAULT_REDIS_URL = "redis://:smarttest_redis_dev@127.0.0.1:6379/0"


class Settings(BaseSettings):
    """Application settings loaded from environment / .env.

    Development-only defaults are intentionally localhost-bound. See
    docs/SECURITY.md before changing them.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "SmartTest"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    api_v1_prefix: str = "/api/v1"
    request_id_header: str = "X-Request-ID"

    database_url: str = DEFAULT_DATABASE_URL
    redis_url: str = DEFAULT_REDIS_URL
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_task_always_eager: bool = False

    storage_root: Path = PROJECT_ROOT / "storage"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SMARTTEST_SECRET_KEY", "SECRET_KEY"),
    )
    api_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SMARTTEST_API_TOKEN", "API_TOKEN"),
    )
    dev_allowed_targets: str = Field(
        default="http://127.0.0.1:8001",
        validation_alias=AliasChoices("SMARTTEST_DEV_ALLOWED_TARGETS", "DEV_ALLOWED_TARGETS"),
    )
    execution_mode: str = Field(
        default="local",
        validation_alias=AliasChoices("SMARTTEST_EXECUTION_MODE", "EXECUTION_MODE"),
    )
    allow_local_execution: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "SMARTTEST_ALLOW_LOCAL_EXECUTION", "ALLOW_LOCAL_EXECUTION"
        ),
    )
    browser_channel: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PLAYWRIGHT_CHANNEL", "BROWSER_CHANNEL"),
    )

    max_request_body_bytes: int = 1_048_576
    default_page_size: int = 20
    max_page_size: int = 100

    @field_validator(
        "secret_key",
        "api_token",
        "celery_broker_url",
        "celery_result_backend",
        "browser_channel",
        mode="before",
    )
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("storage_root", mode="before")
    @classmethod
    def _resolve_storage_root(cls, value: object) -> Path:
        path = Path(str(value)).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local", "test"}

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def dev_allowed_origin_list(self) -> list[str]:
        if not self.is_development:
            return []
        return [
            item.strip().rstrip("/")
            for item in self.dev_allowed_targets.split(",")
            if item.strip()
        ]

    @property
    def secret_key_file(self) -> Path:
        return PROJECT_ROOT / ".dev" / "secret.key"

    @property
    def access_log_enabled(self) -> bool:
        return self.debug


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

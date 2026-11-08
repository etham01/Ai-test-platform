from __future__ import annotations

import time
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers.base import LLMError, LLMProvider
from app.ai.providers.mock import MockLLMProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.core.errors import AppError
from app.core.security import (
    SecretConfigurationError,
    decrypt_secret,
    encrypt_secret,
    mask_secret,
)
from app.models.llm_config import LLMConfig
from app.schemas.llm_config import LLMConfigRead, LLMConfigUpdate, LLMTestRequest


class LLMConfigService:
    @staticmethod
    def get(db: Session, project_id: int) -> LLMConfig | None:
        return db.scalar(select(LLMConfig).where(LLMConfig.project_id == project_id))

    @staticmethod
    def read(db: Session, project_id: int) -> LLMConfigRead:
        config = LLMConfigService.get(db, project_id)
        if config is None:
            return LLMConfigRead(
                project_id=project_id,
                provider="mock",
                base_url=None,
                model="mock-v1",
                configured=True,
                key_hint=None,
                temperature=0.2,
                timeout_seconds=60,
                max_retries=2,
                is_mock=True,
                updated_at=None,
            )
        is_mock = config.provider == "mock"
        return LLMConfigRead(
            project_id=project_id,
            provider=config.provider,
            base_url=config.base_url,
            model=config.model,
            configured=is_mock or bool(config.api_key_encrypted),
            key_hint=config.api_key_hint,
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            is_mock=is_mock,
            updated_at=config.updated_at,
        )

    @staticmethod
    def _validate_base_url(value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise AppError(
                "INVALID_LLM_BASE_URL",
                "LLM base_url 必须是合法的 http/https 地址",
                status_code=422,
            )
        if parsed.username or parsed.password:
            raise AppError(
                "INVALID_LLM_BASE_URL",
                "LLM base_url 不能包含用户名或密码",
                status_code=422,
            )
        return value

    @staticmethod
    def upsert(
        db: Session, project_id: int, payload: LLMConfigUpdate
    ) -> LLMConfig:
        config = LLMConfigService.get(db, project_id)
        if config is None:
            config = LLMConfig(
                project_id=project_id,
                provider=payload.provider,
                model="mock-v1" if payload.provider == "mock" else (payload.model or ""),
                temperature=payload.temperature,
                timeout_seconds=payload.timeout_seconds,
                max_retries=payload.max_retries,
                is_active=True,
            )
            db.add(config)

        config.provider = payload.provider
        config.temperature = payload.temperature
        config.timeout_seconds = payload.timeout_seconds
        config.max_retries = payload.max_retries
        config.is_active = True

        if payload.provider == "mock":
            config.base_url = None
            config.model = "mock-v1"
            config.api_key_encrypted = None
            config.api_key_hint = None
        else:
            base_url = payload.base_url or config.base_url
            model = payload.model or config.model
            if not base_url or not model:
                raise AppError(
                    "LLM_CONFIG_INCOMPLETE",
                    "真实模型需要 base_url 和 model",
                    status_code=422,
                )
            config.base_url = LLMConfigService._validate_base_url(base_url)
            config.model = model.strip()
            if payload.clear_api_key:
                config.api_key_encrypted = None
                config.api_key_hint = None
            elif payload.api_key:
                try:
                    config.api_key_encrypted = encrypt_secret(payload.api_key)
                except SecretConfigurationError as exc:
                    raise AppError(
                        "SECRET_KEY_INVALID", str(exc), status_code=500
                    ) from exc
                config.api_key_hint = mask_secret(payload.api_key)

        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def build_provider(db: Session, project_id: int) -> LLMProvider:
        config = LLMConfigService.get(db, project_id)
        if config is None or config.provider == "mock":
            return MockLLMProvider()
        if not config.is_active:
            raise LLMError("LLM_NOT_CONFIGURED", "LLM 配置已停用")
        if not config.base_url or not config.api_key_encrypted:
            raise LLMError(
                "LLM_NOT_CONFIGURED", "真实模型尚未配置 base_url 或 API Key"
            )
        try:
            api_key = decrypt_secret(config.api_key_encrypted)
        except SecretConfigurationError as exc:
            raise LLMError("LLM_KEY_DECRYPT_FAILED", str(exc)) from exc
        return OpenAICompatibleProvider(
            base_url=config.base_url,
            api_key=api_key,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            temperature=config.temperature,
        )

    @staticmethod
    def test(
        db: Session,
        project_id: int,
        overrides: LLMTestRequest | None = None,
    ) -> dict:
        provider: LLMProvider | None = None
        config = LLMConfigService.get(db, project_id)
        started = time.perf_counter()
        try:
            if overrides and (overrides.base_url or overrides.api_key):
                base_url = overrides.base_url
                api_key = overrides.api_key
                model = overrides.model or (config.model if config else None)
                if not base_url or not api_key or not model:
                    raise LLMError(
                        "LLM_CONFIG_INCOMPLETE",
                        "临时测试需要 base_url、api_key 和 model",
                    )
                provider = OpenAICompatibleProvider(
                    base_url=LLMConfigService._validate_base_url(base_url),
                    api_key=api_key,
                    model=model,
                    timeout_seconds=config.timeout_seconds if config else 30,
                    max_retries=0,
                    temperature=0,
                )
            else:
                provider = LLMConfigService.build_provider(db, project_id)
            return provider.test_connection()
        except (LLMError, AppError) as exc:
            return {
                "ok": False,
                "is_mock": bool(config and config.provider == "mock"),
                "provider": config.provider if config else "mock",
                "model": config.model if config else "mock-v1",
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "message": getattr(exc, "message", str(exc)),
            }
        finally:
            if provider is not None:
                provider.close()

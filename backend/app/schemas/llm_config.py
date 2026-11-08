from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

LLMProviderName = Literal["openai_compatible", "mock"]


class LLMConfigUpdate(BaseModel):
    provider: LLMProviderName = "mock"
    base_url: str | None = Field(default=None, max_length=512)
    model: str | None = Field(default=None, max_length=128)
    api_key: str | None = Field(default=None, max_length=4096)
    clear_api_key: bool = False
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    max_retries: int = Field(default=2, ge=0, le=5)


class LLMConfigRead(BaseModel):
    project_id: int
    provider: str
    base_url: str | None
    model: str
    configured: bool
    key_hint: str | None
    temperature: float
    timeout_seconds: int
    max_retries: int
    is_mock: bool
    updated_at: datetime | None


class LLMTestRequest(BaseModel):
    # Optional ad-hoc override without persisting the key.
    base_url: str | None = Field(default=None, max_length=512)
    model: str | None = Field(default=None, max_length=128)
    api_key: str | None = Field(default=None, max_length=4096)


class LLMTestResult(BaseModel):
    ok: bool
    is_mock: bool
    provider: str
    model: str
    latency_ms: int
    message: str

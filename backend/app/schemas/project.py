from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

BrowserType = Literal["chromium", "chrome", "msedge"]


def _validate_base_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("base_url 不能为空")
    if len(value) > 2048:
        raise ValueError("base_url 过长")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base_url 只支持 http/https")
    if not parsed.hostname:
        raise ValueError("base_url 缺少主机名")
    if parsed.username or parsed.password:
        raise ValueError("base_url 不能包含用户名或密码")
    if parsed.port is not None and not (1 <= parsed.port <= 65535):
        raise ValueError("base_url 端口非法")
    return value


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=5000)
    base_url: str = Field(max_length=2048)
    browser_type: BrowserType = "chromium"
    scan_config: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("项目名不能为空")
        return value

    @field_validator("base_url")
    @classmethod
    def _check_base_url(cls, value: str) -> str:
        return _validate_base_url(value)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=5000)
    base_url: str | None = Field(default=None, max_length=2048)
    browser_type: BrowserType | None = None
    scan_config: dict[str, Any] | None = None
    status: Literal["active", "archived"] | None = None

    @field_validator("name")
    @classmethod
    def _strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("项目名不能为空")
        return value

    @field_validator("base_url")
    @classmethod
    def _check_optional_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_base_url(value)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: str | None
    base_url: str
    browser_type: str
    scan_config: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectOverview(BaseModel):
    project: ProjectRead
    counts: dict[str, int] = Field(default_factory=dict)

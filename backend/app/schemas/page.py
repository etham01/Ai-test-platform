from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PageScanRequest(BaseModel):
    url: str | None = Field(default=None, max_length=2048)
    timeout_seconds: int = Field(default=15, ge=3, le=120)
    wait_after_load_ms: int = Field(default=800, ge=0, le=5000)


class PageExploreRequest(BaseModel):
    start_url: str | None = Field(default=None, max_length=2048)
    max_pages: int = Field(default=8, ge=1, le=50)
    max_depth: int = Field(default=2, ge=0, le=5)
    timeout_seconds: int = Field(default=15, ge=3, le=120)
    total_timeout_seconds: int = Field(default=300, ge=10, le=900)
    wait_after_load_ms: int = Field(default=800, ge=0, le=5000)
    extra_urls: list[str] = Field(default_factory=list, max_length=20)


class PageElementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    element_type: str
    tag: str
    role: str | None
    accessible_name: str | None
    label: str | None
    placeholder: str | None
    text: str | None
    element_id: str | None
    name: str | None
    input_type: str | None
    href: str | None
    selector_candidates: dict[str, Any] | None
    is_sensitive: bool
    attributes: dict[str, Any] | None


class PageSummary(BaseModel):
    id: int
    url: str
    title: str | None
    depth: int
    status: str
    http_status: int | None
    source: str
    element_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class PageDetail(PageSummary):
    normalized_url: str
    content_type: str | None
    text_summary: str | None
    screenshot_url: str | None
    dom_url: str | None
    elements: list[PageElementRead]


class PageRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_page_id: int
    to_page_id: int | None
    target_url: str | None
    relation_type: str
    source: str
    confidence: float
    evidence: dict[str, Any] | None
    created_at: datetime


class PageRelationList(BaseModel):
    items: list[PageRelationRead]
    total: int

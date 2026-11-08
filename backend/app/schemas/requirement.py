from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RequirementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=64_000)
    related_page_ids: list[int] = Field(default_factory=list)
    generation_config: dict[str, Any] | None = None


class RequirementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    content: str | None = Field(default=None, min_length=1, max_length=64_000)
    related_page_ids: list[int] | None = None
    generation_config: dict[str, Any] | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|archived)$")


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    content: str
    related_page_ids: list[int] | None
    generation_config: dict[str, Any] | None
    status: str
    created_by: int | None
    created_at: datetime
    updated_at: datetime

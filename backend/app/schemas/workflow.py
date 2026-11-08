from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowAnalyzeRequest(BaseModel):
    requirement_id: int | None = None
    page_ids: list[int] = Field(default_factory=list, max_length=50)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    steps: list[dict[str, Any]] | None = None
    involved_page_ids: list[int] | None = None
    uncertainty: str | None = None
    status: str | None = Field(default=None, pattern="^(inferred|confirmed|edited|archived)$")


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    requirement_id: int | None
    name: str
    description: str | None
    steps: list[dict[str, Any]]
    involved_page_ids: list[int] | None
    uncertainty: str | None
    status: str
    source: str
    generation_record_id: int | None
    created_at: datetime
    updated_at: datetime

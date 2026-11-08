from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerateScriptsRequest(BaseModel):
    test_case_ids: list[int] = Field(min_length=1, max_length=20)


class ScriptUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=60_000)


class ScriptSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    test_case_id: int
    version: int
    filename: str
    content_hash: str
    status: str
    validation_report: dict[str, Any] | None
    generation_source: str
    generation_record_id: int | None
    created_at: datetime
    updated_at: datetime


class ScriptDetail(ScriptSummary):
    content: str

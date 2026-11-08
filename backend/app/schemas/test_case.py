from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestCaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    module: str | None = Field(default=None, max_length=128)
    priority: str | None = Field(default=None, pattern="^P[0-3]$")
    preconditions: list[Any] | None = None
    related_page_ids: list[int] | None = None
    steps: list[dict[str, Any]] | None = None
    test_data: dict[str, Any] | None = None
    expected_result: str | None = None
    assertions: list[dict[str, Any]] | None = None
    assumptions: list[Any] | None = None
    status: str | None = Field(
        default=None, pattern="^(draft|needs_review|confirmed|archived)$"
    )


class TestCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    requirement_id: int | None
    case_code: str
    title: str
    module: str | None
    priority: str
    preconditions: list[Any] | None
    related_page_ids: list[int] | None
    steps: list[dict[str, Any]]
    test_data: dict[str, Any] | None
    expected_result: str | None
    assertions: list[dict[str, Any]]
    assumptions: list[Any] | None
    status: str
    generation_source: str
    generation_record_id: int | None
    created_at: datetime
    updated_at: datetime


class GenerateCasesRequest(BaseModel):
    requirement_id: int
    page_ids: list[int] = Field(default_factory=list, max_length=50)
    max_cases: int = Field(default=5, ge=1, le=10)
    include_workflow_ids: list[int] = Field(default_factory=list, max_length=10)


class GenerationRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    task_type: str
    prompt_version: str
    provider: str
    model: str
    is_mock: bool
    input_summary: str | None
    output_summary: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    duration_ms: int | None
    status: str
    error: str | None
    created_at: datetime


class FailureAnalyzeRequest(BaseModel):
    execution_id: int = Field(ge=1)
    result_id: int = Field(ge=1)

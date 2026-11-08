from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ExecutionCreate(BaseModel):
    script_ids: list[int] = Field(min_length=1, max_length=20)
    timeout_seconds: int = Field(default=120, ge=10, le=600)
    mode: Literal["local", "docker"] = "local"


class ExecutionCreated(BaseModel):
    execution_id: int
    task_id: str


class ExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    task_id: str | None
    status: str
    mode: str
    timeout_seconds: int
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    started_at: datetime | None
    finished_at: datetime | None
    report_url: str | None
    log_url: str | None
    error_message: str | None
    created_at: datetime


class TestResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_id: int
    script_id: int | None
    test_case_id: int | None
    node_id: str | None
    test_name: str
    status: str
    duration_ms: int | None
    failure_message: str | None
    traceback: str | None
    screenshot_url: str | None
    failure_analysis: dict[str, Any] | None
    created_at: datetime


class ExecutionResults(BaseModel):
    items: list[TestResultRead]
    total: int


class ExecutionCancelResponse(BaseModel):
    execution_id: int
    task_id: str | None
    status: str
    cancel_requested: bool

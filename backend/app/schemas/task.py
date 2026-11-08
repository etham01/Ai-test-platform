from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskStatus, TaskType


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    project_id: int | None
    task_type: TaskType
    status: TaskStatus
    progress: int
    message: str | None
    result: dict[str, Any] | None
    error: str | None
    cancel_requested: bool
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class TaskCreated(BaseModel):
    task_id: str
    task_type: TaskType


class TaskLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    level: str
    message: str
    created_at: datetime


class TaskLogList(BaseModel):
    items: list[TaskLogRead]
    total: int


class DebugTaskCreate(BaseModel):
    message: str = Field(default="pong", min_length=1, max_length=200)
    sleep_seconds: float = Field(default=0.0, ge=0.0, le=30.0)


class TaskCancelled(BaseModel):
    task_id: str
    status: TaskStatus
    cancel_requested: bool

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import DbSession
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import get_request_id
from app.models.enums import TaskStatus, TaskType
from app.schemas.common import ApiResponse
from app.schemas.task import (
    DebugTaskCreate,
    TaskCancelled,
    TaskCreated,
    TaskLogList,
    TaskLogRead,
    TaskRead,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

TaskId = Annotated[str, Path(min_length=8, max_length=64)]


@router.post(
    "/debug",
    response_model=ApiResponse[TaskCreated],
    status_code=status.HTTP_202_ACCEPTED,
    summary="投递调试任务（仅开发环境）",
)
def create_debug_task(payload: DebugTaskCreate, db: DbSession) -> ApiResponse[TaskCreated]:
    if not settings.is_development:
        raise AppError("DEBUG_DISABLED", "调试任务仅开发环境可用", status_code=404)
    task = TaskService.create_debug(
        db,
        project_id=None,
        message=payload.message,
        sleep_seconds=payload.sleep_seconds,
    )
    return ApiResponse(
        data=TaskCreated(
            task_id=task.task_id,
            task_type=TaskType(task.task_type),
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/{task_id}",
    response_model=ApiResponse[TaskRead],
    summary="任务状态",
)
def get_task(task_id: TaskId, db: DbSession) -> ApiResponse[TaskRead]:
    task = TaskService.get_or_404(db, task_id)
    return ApiResponse(
        data=TaskRead.model_validate(task),
        request_id=get_request_id(),
    )


@router.get(
    "/{task_id}/logs",
    response_model=ApiResponse[TaskLogList],
    summary="任务日志",
)
def get_task_logs(
    task_id: TaskId,
    db: DbSession,
    limit: int = Query(default=200, ge=1, le=500),
) -> ApiResponse[TaskLogList]:
    logs, total = TaskService.list_logs(db, task_id, limit=limit)
    return ApiResponse(
        data=TaskLogList(
            items=[TaskLogRead.model_validate(item) for item in logs],
            total=total,
        ),
        request_id=get_request_id(),
    )


@router.post(
    "/{task_id}/cancel",
    response_model=ApiResponse[TaskCancelled],
    summary="取消任务",
)
def cancel_task(task_id: TaskId, db: DbSession) -> ApiResponse[TaskCancelled]:
    task = TaskService.get_or_404(db, task_id)
    task = TaskService.cancel(db, task)
    return ApiResponse(
        data=TaskCancelled(
            task_id=task.task_id,
            status=TaskStatus(task.status),
            cancel_requested=task.cancel_requested,
        ),
        request_id=get_request_id(),
    )

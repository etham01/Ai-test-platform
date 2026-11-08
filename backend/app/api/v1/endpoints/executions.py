from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession, Pagination, ProjectDep
from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.core.logging import get_request_id
from app.core.paths import PathSecurityError, resolve_within
from app.schemas.common import ApiResponse, Paginated
from app.schemas.execution import (
    ExecutionCancelResponse,
    ExecutionCreate,
    ExecutionCreated,
    ExecutionRead,
    ExecutionResults,
)
from app.services.execution_service import ExecutionService
from app.services.project_service import ProjectService

router = APIRouter(tags=["executions"])
ExecutionId = Annotated[int, Path(ge=1)]
ResultId = Annotated[int, Path(ge=1)]


def _owned_execution(db: DbSession, execution_id: int, current_user: CurrentUser):
    execution = ExecutionService.get_or_404(db, execution_id)
    ProjectService.get_or_404(db, execution.project_id, current_user.id)
    return execution


@router.post(
    "/projects/{project_id}/executions",
    response_model=ApiResponse[ExecutionCreated],
    summary="创建测试执行（异步）",
)
def create_execution(
    payload: ExecutionCreate,
    project: ProjectDep,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ExecutionCreated]:
    execution, task = ExecutionService.create(
        db,
        project_id=project.id,
        user_id=current_user.id,
        script_ids=payload.script_ids,
        timeout_seconds=payload.timeout_seconds,
        mode=payload.mode,
    )
    return ApiResponse(
        data=ExecutionCreated(execution_id=execution.id, task_id=task.task_id),
        request_id=get_request_id(),
    )


@router.get(
    "/projects/{project_id}/executions",
    response_model=ApiResponse[Paginated[ExecutionRead]],
    summary="执行历史",
)
def list_executions(
    project: ProjectDep,
    db: DbSession,
    pagination: Pagination,
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            pattern="^(pending|running|passed|failed|error|timeout|cancelled)$",
        ),
    ] = None,
) -> ApiResponse[Paginated[ExecutionRead]]:
    page, page_size = pagination
    items, total = ExecutionService.list(
        db, project.id, page, page_size, status_filter
    )
    return ApiResponse(
        data=Paginated[ExecutionRead](
            items=[ExecutionService.to_read(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/executions/{execution_id}",
    response_model=ApiResponse[ExecutionRead],
    summary="执行详情",
)
def get_execution(
    execution_id: ExecutionId,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ExecutionRead]:
    execution = _owned_execution(db, execution_id, current_user)
    return ApiResponse(
        data=ExecutionService.to_read(execution),
        request_id=get_request_id(),
    )


@router.get(
    "/executions/{execution_id}/results",
    response_model=ApiResponse[ExecutionResults],
    summary="逐条测试结果",
)
def get_execution_results(
    execution_id: ExecutionId,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ExecutionResults]:
    execution = _owned_execution(db, execution_id, current_user)
    results = ExecutionService.list_results(db, execution.id)
    return ApiResponse(
        data=ExecutionResults(
            items=[ExecutionService.to_result_read(item) for item in results],
            total=len(results),
        ),
        request_id=get_request_id(),
    )


@router.post(
    "/executions/{execution_id}/cancel",
    response_model=ApiResponse[ExecutionCancelResponse],
    summary="取消执行",
)
def cancel_execution(
    execution_id: ExecutionId,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ExecutionCancelResponse]:
    execution = _owned_execution(db, execution_id, current_user)
    result = ExecutionService.cancel(db, execution)
    return ApiResponse(data=result, request_id=get_request_id())


def _file_response(
    execution,
    attribute: str,
    media_type: str,
    filename: str,
    *,
    attachment: bool = True,
) -> FileResponse:
    relative = getattr(execution, attribute)
    if not relative:
        raise NotFoundError("FILE_NOT_FOUND", "该执行没有对应的文件")
    try:
        path = resolve_within(settings.storage_root, relative)
    except PathSecurityError as exc:
        raise AppError("STORAGE_PATH_INVALID", "文件路径非法", status_code=400) from exc
    if not path.is_file():
        raise NotFoundError("FILE_NOT_FOUND", "文件不存在")
    headers = {}
    if attachment:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return FileResponse(path, media_type=media_type, headers=headers)


@router.get(
    "/executions/{execution_id}/report",
    summary="HTML 测试报告",
    response_class=FileResponse,
)
def download_report(
    execution_id: ExecutionId,
    db: DbSession,
    current_user: CurrentUser,
) -> FileResponse:
    execution = _owned_execution(db, execution_id, current_user)
    return _file_response(
        execution,
        "report_path",
        "text/html",
        f"smarttest-execution-{execution.id}.html",
    )


@router.get(
    "/executions/{execution_id}/log",
    summary="执行日志",
    response_class=FileResponse,
)
def download_log(
    execution_id: ExecutionId,
    db: DbSession,
    current_user: CurrentUser,
) -> FileResponse:
    execution = _owned_execution(db, execution_id, current_user)
    return _file_response(
        execution,
        "log_path",
        "text/plain",
        f"smarttest-execution-{execution.id}.log",
    )


@router.get(
    "/test-results/{result_id}/screenshot",
    summary="失败截图",
    response_class=FileResponse,
)
def result_screenshot(
    result_id: ResultId,
    db: DbSession,
    current_user: CurrentUser,
) -> FileResponse:
    result = ExecutionService.get_result_or_404(db, result_id)
    ProjectService.get_or_404(db, result.project_id, current_user.id)
    if not result.screenshot_path:
        raise NotFoundError("FILE_NOT_FOUND", "该结果没有截图")
    try:
        path = resolve_within(settings.storage_root, result.screenshot_path)
    except PathSecurityError as exc:
        raise AppError("STORAGE_PATH_INVALID", "文件路径非法", status_code=400) from exc
    if not path.is_file():
        raise NotFoundError("FILE_NOT_FOUND", "截图不存在")
    return FileResponse(path, media_type="image/png")

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, Response

from app.api.deps import CurrentUser, DbSession, Pagination, ProjectDep
from app.core.logging import get_request_id
from app.models.enums import TaskType
from app.schemas.common import ApiResponse, Paginated
from app.schemas.script import (
    GenerateScriptsRequest,
    ScriptDetail,
    ScriptSummary,
    ScriptUpdate,
)
from app.schemas.task import TaskCreated
from app.services.project_service import ProjectService
from app.services.script_service import ScriptService
from app.services.task_service import TaskService
from app.services.test_case_service import TestCaseService
from app.tasks.script_tasks import generate_scripts_task

router = APIRouter(tags=["scripts"])
ScriptId = Annotated[int, Path(ge=1)]


def _owned_script(db: DbSession, script_id: int, current_user: CurrentUser):
    script = ScriptService.get_or_404(db, script_id)
    ProjectService.get_or_404(db, script.project_id, current_user.id)
    return script


@router.post(
    "/projects/{project_id}/ai/generate-scripts",
    response_model=ApiResponse[TaskCreated],
    summary="LLM/Mock 生成 Pytest + Playwright 脚本（异步）",
)
def generate_scripts(
    payload: GenerateScriptsRequest,
    project: ProjectDep,
    db: DbSession,
) -> ApiResponse[TaskCreated]:
    for case_id in payload.test_case_ids:
        TestCaseService.get_or_404(db, case_id, project.id)
    task = TaskService.create_and_dispatch(
        db,
        project.id,
        TaskType.SCRIPT_GENERATION,
        lambda task_id: generate_scripts_task.delay(
            task_id, project.id, payload.test_case_ids
        ),
    )
    return ApiResponse(
        data=TaskCreated(
            task_id=task.task_id, task_type=TaskType.SCRIPT_GENERATION
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/projects/{project_id}/test-scripts",
    response_model=ApiResponse[Paginated[ScriptSummary]],
    summary="脚本列表",
)
def list_scripts(
    project: ProjectDep,
    db: DbSession,
    pagination: Pagination,
    test_case_id: int | None = Query(default=None, ge=1),
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(draft|validated|rejected|archived)$"),
    ] = None,
) -> ApiResponse[Paginated[ScriptSummary]]:
    page, page_size = pagination
    items, total = ScriptService.list(
        db,
        project.id,
        page,
        page_size,
        test_case_id=test_case_id,
        status=status_filter,
    )
    return ApiResponse(
        data=Paginated[ScriptSummary](
            items=[ScriptService.to_summary(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/test-scripts/{script_id}",
    response_model=ApiResponse[ScriptDetail],
    summary="脚本详情",
)
def get_script(
    script_id: ScriptId,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ScriptDetail]:
    script = _owned_script(db, script_id, current_user)
    return ApiResponse(
        data=ScriptService.to_detail(script),
        request_id=get_request_id(),
    )


@router.put(
    "/test-scripts/{script_id}",
    response_model=ApiResponse[ScriptDetail],
    summary="编辑脚本（生成新版本并重新校验）",
)
def update_script(
    script_id: ScriptId,
    payload: ScriptUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ScriptDetail]:
    script = _owned_script(db, script_id, current_user)
    new_script = ScriptService.update_content(db, script, payload.content)
    return ApiResponse(
        data=ScriptService.to_detail(new_script),
        request_id=get_request_id(),
    )


@router.post(
    "/test-scripts/{script_id}/validate",
    response_model=ApiResponse[ScriptDetail],
    summary="重新校验脚本",
)
def validate_script_endpoint(
    script_id: ScriptId,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ScriptDetail]:
    script = _owned_script(db, script_id, current_user)
    script = ScriptService.revalidate(db, script)
    return ApiResponse(
        data=ScriptService.to_detail(script),
        request_id=get_request_id(),
    )


@router.get(
    "/test-scripts/{script_id}/download",
    summary="下载脚本",
    response_class=Response,
)
def download_script(
    script_id: ScriptId,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    script = _owned_script(db, script_id, current_user)
    return Response(
        content=script.content.encode("utf-8"),
        media_type="text/x-python",
        headers={
            "Content-Disposition": f'attachment; filename="{script.filename}"'
        },
    )

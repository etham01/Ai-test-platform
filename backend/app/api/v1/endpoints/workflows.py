from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.deps import CurrentUser, DbSession, Pagination, ProjectDep
from app.core.logging import get_request_id
from app.models.enums import TaskType
from app.schemas.common import ApiResponse, Paginated
from app.schemas.task import TaskCreated
from app.schemas.workflow import (
    WorkflowAnalyzeRequest,
    WorkflowRead,
    WorkflowUpdate,
)
from app.services.project_service import ProjectService
from app.services.requirement_service import RequirementService
from app.services.task_service import TaskService
from app.services.workflow_service import WorkflowService
from app.tasks.generation_tasks import analyze_workflows_task

router = APIRouter(tags=["workflows"])
WorkflowId = Annotated[int, Path(ge=1)]


def _owned_workflow(db: DbSession, workflow_id: int, current_user: CurrentUser):
    workflow = WorkflowService.get_or_404(db, workflow_id)
    ProjectService.get_or_404(db, workflow.project_id, current_user.id)
    return workflow


@router.post(
    "/projects/{project_id}/workflows/analyze",
    response_model=ApiResponse[TaskCreated],
    summary="分析业务流程（异步）",
)
def analyze_workflows(
    payload: WorkflowAnalyzeRequest,
    project: ProjectDep,
    db: DbSession,
) -> ApiResponse[TaskCreated]:
    if payload.requirement_id is not None:
        RequirementService.get_or_404(db, payload.requirement_id, project.id)
    page_ids = RequirementService.validate_page_ids(db, project.id, payload.page_ids)
    task = TaskService.create_and_dispatch(
        db,
        project.id,
        TaskType.WORKFLOW_ANALYSIS,
        lambda task_id: analyze_workflows_task.delay(
            task_id,
            project.id,
            payload.requirement_id,
            page_ids,
        ),
    )
    return ApiResponse(
        data=TaskCreated(
            task_id=task.task_id, task_type=TaskType.WORKFLOW_ANALYSIS
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/projects/{project_id}/workflows",
    response_model=ApiResponse[Paginated[WorkflowRead]],
    summary="业务流程列表",
)
def list_workflows(
    project: ProjectDep,
    db: DbSession,
    pagination: Pagination,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(inferred|confirmed|edited|archived)$"),
    ] = None,
) -> ApiResponse[Paginated[WorkflowRead]]:
    page, page_size = pagination
    items, total = WorkflowService.list(db, project.id, page, page_size, status_filter)
    return ApiResponse(
        data=Paginated[WorkflowRead](
            items=[WorkflowRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/workflows/{workflow_id}",
    response_model=ApiResponse[WorkflowRead],
    summary="业务流程详情",
)
def get_workflow(
    workflow_id: WorkflowId,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[WorkflowRead]:
    workflow = _owned_workflow(db, workflow_id, current_user)
    return ApiResponse(
        data=WorkflowRead.model_validate(workflow),
        request_id=get_request_id(),
    )


@router.put(
    "/workflows/{workflow_id}",
    response_model=ApiResponse[WorkflowRead],
    summary="编辑/确认业务流程",
)
def update_workflow(
    workflow_id: WorkflowId,
    payload: WorkflowUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[WorkflowRead]:
    workflow = _owned_workflow(db, workflow_id, current_user)
    if payload.involved_page_ids is not None:
        RequirementService.validate_page_ids(
            db, workflow.project_id, payload.involved_page_ids
        )
    workflow = WorkflowService.update(db, workflow, payload)
    return ApiResponse(
        data=WorkflowRead.model_validate(workflow),
        request_id=get_request_id(),
    )


@router.delete(
    "/workflows/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除业务流程",
)
def delete_workflow(
    workflow_id: WorkflowId,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    workflow = _owned_workflow(db, workflow_id, current_user)
    WorkflowService.delete(db, workflow)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

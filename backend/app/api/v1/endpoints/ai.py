from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DbSession, ProjectDep
from app.core.logging import get_request_id
from app.models.enums import TaskType
from app.schemas.common import ApiResponse
from app.schemas.task import TaskCreated
from app.schemas.test_case import (
    FailureAnalyzeRequest,
    GenerateCasesRequest,
    GenerationRecordRead,
)
from app.services.execution_service import ExecutionService
from app.services.generation_service import GenerationService
from app.services.requirement_service import RequirementService
from app.services.task_service import TaskService
from app.tasks.failure_tasks import analyze_failure_task
from app.tasks.generation_tasks import generate_cases_task

router = APIRouter(prefix="/projects/{project_id}/ai", tags=["ai"])


@router.post(
    "/generate-cases",
    response_model=ApiResponse[TaskCreated],
    summary="LLM/Mock 生成测试用例（异步）",
)
def generate_cases(
    payload: GenerateCasesRequest,
    project: ProjectDep,
    db: DbSession,
) -> ApiResponse[TaskCreated]:
    requirement = RequirementService.get_or_404(
        db, payload.requirement_id, project.id
    )
    page_ids = RequirementService.validate_page_ids(
        db,
        project.id,
        payload.page_ids or requirement.related_page_ids or [],
    )
    task = TaskService.create_and_dispatch(
        db,
        project.id,
        TaskType.CASE_GENERATION,
        lambda task_id: generate_cases_task.delay(
            task_id,
            project.id,
            requirement.id,
            page_ids,
            payload.max_cases,
            payload.include_workflow_ids,
        ),
    )
    return ApiResponse(
        data=TaskCreated(
            task_id=task.task_id, task_type=TaskType.CASE_GENERATION
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/generation-records",
    response_model=ApiResponse[list[GenerationRecordRead]],
    summary="AI 生成记录",
)
def list_generation_records(
    project: ProjectDep,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> ApiResponse[list[GenerationRecordRead]]:
    records = GenerationService.list_records(db, project.id, limit=limit)
    return ApiResponse(
        data=[GenerationRecordRead.model_validate(record) for record in records],
        request_id=get_request_id(),
    )


@router.post(
    "/analyze-failure",
    response_model=ApiResponse[TaskCreated],
    summary="分析失败结果（异步）",
)
def analyze_failure(
    payload: FailureAnalyzeRequest,
    project: ProjectDep,
    db: DbSession,
) -> ApiResponse[TaskCreated]:
    execution = ExecutionService.get_or_404(db, payload.execution_id)
    if execution.project_id != project.id:
        from app.core.errors import NotFoundError

        raise NotFoundError("EXECUTION_NOT_FOUND", "执行记录不属于当前项目")
    result = ExecutionService.get_result_or_404(db, payload.result_id)
    if result.execution_id != execution.id:
        from app.core.errors import NotFoundError

        raise NotFoundError("RESULT_NOT_FOUND", "测试结果不属于该执行")
    if result.status not in {"failed", "error"}:
        from app.core.errors import ConflictError

        raise ConflictError("RESULT_NOT_FAILED", "只有失败/错误结果可以分析")
    task = TaskService.create_and_dispatch(
        db,
        project.id,
        TaskType.FAILURE_ANALYSIS,
        lambda task_id: analyze_failure_task.delay(
            task_id, project.id, execution.id, result.id
        ),
    )
    return ApiResponse(
        data=TaskCreated(
            task_id=task.task_id, task_type=TaskType.FAILURE_ANALYSIS
        ),
        request_id=get_request_id(),
    )

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.deps import CurrentUser, DbSession, Pagination, ProjectDep
from app.core.logging import get_request_id
from app.schemas.common import ApiResponse, Paginated
from app.schemas.test_case import TestCaseRead, TestCaseUpdate
from app.services.project_service import ProjectService
from app.services.requirement_service import RequirementService
from app.services.test_case_service import TestCaseService

router = APIRouter(tags=["test-cases"])
CaseId = Annotated[int, Path(ge=1)]


def _owned_case(db: DbSession, case_id: int, current_user: CurrentUser):
    case = TestCaseService.get_or_404(db, case_id)
    ProjectService.get_or_404(db, case.project_id, current_user.id)
    return case


@router.get(
    "/projects/{project_id}/test-cases",
    response_model=ApiResponse[Paginated[TestCaseRead]],
    summary="测试用例列表",
)
def list_test_cases(
    project: ProjectDep,
    db: DbSession,
    pagination: Pagination,
    requirement_id: int | None = Query(default=None, ge=1),
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(draft|needs_review|confirmed|archived)$"),
    ] = None,
    priority: Annotated[str | None, Query(pattern="^P[0-3]$")] = None,
) -> ApiResponse[Paginated[TestCaseRead]]:
    page, page_size = pagination
    items, total = TestCaseService.list(
        db,
        project.id,
        page,
        page_size,
        requirement_id=requirement_id,
        status=status_filter,
        priority=priority,
    )
    return ApiResponse(
        data=Paginated[TestCaseRead](
            items=[TestCaseRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/test-cases/{case_id}",
    response_model=ApiResponse[TestCaseRead],
    summary="测试用例详情",
)
def get_test_case(
    case_id: CaseId,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[TestCaseRead]:
    case = _owned_case(db, case_id, current_user)
    return ApiResponse(
        data=TestCaseRead.model_validate(case),
        request_id=get_request_id(),
    )


@router.put(
    "/test-cases/{case_id}",
    response_model=ApiResponse[TestCaseRead],
    summary="编辑测试用例",
)
def update_test_case(
    case_id: CaseId,
    payload: TestCaseUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[TestCaseRead]:
    case = _owned_case(db, case_id, current_user)
    if payload.related_page_ids is not None:
        RequirementService.validate_page_ids(
            db, case.project_id, payload.related_page_ids
        )
    case = TestCaseService.update(db, case, payload)
    return ApiResponse(
        data=TestCaseRead.model_validate(case),
        request_id=get_request_id(),
    )


@router.delete(
    "/test-cases/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除测试用例",
)
def delete_test_case(
    case_id: CaseId,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    case = _owned_case(db, case_id, current_user)
    TestCaseService.delete(db, case)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

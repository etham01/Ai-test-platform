from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.deps import CurrentUser, DbSession, Pagination, ProjectDep
from app.core.logging import get_request_id
from app.schemas.common import ApiResponse, Paginated
from app.schemas.requirement import (
    RequirementCreate,
    RequirementRead,
    RequirementUpdate,
)
from app.services.project_service import ProjectService
from app.services.requirement_service import RequirementService

router = APIRouter(tags=["requirements"])
RequirementId = Annotated[int, Path(ge=1)]


def _owned_requirement(db: DbSession, requirement_id: int, current_user: CurrentUser):
    requirement = RequirementService.get_or_404(db, requirement_id)
    ProjectService.get_or_404(db, requirement.project_id, current_user.id)
    return requirement


@router.post(
    "/projects/{project_id}/requirements",
    response_model=ApiResponse[RequirementRead],
    status_code=status.HTTP_201_CREATED,
    summary="创建测试需求",
)
def create_requirement(
    payload: RequirementCreate,
    project: ProjectDep,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[RequirementRead]:
    requirement = RequirementService.create(
        db, project.id, current_user.id, payload
    )
    return ApiResponse(
        data=RequirementRead.model_validate(requirement),
        request_id=get_request_id(),
    )


@router.get(
    "/projects/{project_id}/requirements",
    response_model=ApiResponse[Paginated[RequirementRead]],
    summary="测试需求列表",
)
def list_requirements(
    project: ProjectDep,
    db: DbSession,
    pagination: Pagination,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(draft|active|archived)$"),
    ] = None,
) -> ApiResponse[Paginated[RequirementRead]]:
    page, page_size = pagination
    items, total = RequirementService.list(
        db, project.id, page, page_size, status_filter
    )
    return ApiResponse(
        data=Paginated[RequirementRead](
            items=[RequirementRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/requirements/{requirement_id}",
    response_model=ApiResponse[RequirementRead],
    summary="测试需求详情",
)
def get_requirement(
    requirement_id: RequirementId,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[RequirementRead]:
    requirement = _owned_requirement(db, requirement_id, current_user)
    return ApiResponse(
        data=RequirementRead.model_validate(requirement),
        request_id=get_request_id(),
    )


@router.put(
    "/requirements/{requirement_id}",
    response_model=ApiResponse[RequirementRead],
    summary="更新测试需求",
)
def update_requirement(
    requirement_id: RequirementId,
    payload: RequirementUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[RequirementRead]:
    requirement = _owned_requirement(db, requirement_id, current_user)
    requirement = RequirementService.update(db, requirement, payload)
    return ApiResponse(
        data=RequirementRead.model_validate(requirement),
        request_id=get_request_id(),
    )


@router.delete(
    "/requirements/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除测试需求",
)
def delete_requirement(
    requirement_id: RequirementId,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    requirement = _owned_requirement(db, requirement_id, current_user)
    RequirementService.delete(db, requirement)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

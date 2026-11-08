from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.deps import CurrentUser, DbSession, Pagination
from app.core.logging import get_request_id
from app.schemas.common import ApiResponse, Paginated
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

ProjectId = Annotated[int, Path(ge=1)]


@router.post(
    "",
    response_model=ApiResponse[ProjectRead],
    status_code=status.HTTP_201_CREATED,
    summary="创建项目",
)
def create_project(
    payload: ProjectCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ProjectRead]:
    project = ProjectService.create(db, current_user.id, payload)
    return ApiResponse(
        data=ProjectRead.model_validate(project),
        request_id=get_request_id(),
    )


@router.get(
    "",
    response_model=ApiResponse[Paginated[ProjectRead]],
    summary="项目列表",
)
def list_projects(
    db: DbSession,
    current_user: CurrentUser,
    pagination: Pagination,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(active|archived)$"),
    ] = None,
) -> ApiResponse[Paginated[ProjectRead]]:
    page, page_size = pagination
    items, total = ProjectService.list(
        db, current_user.id, page, page_size, status_filter
    )
    return ApiResponse(
        data=Paginated[ProjectRead](
            items=[ProjectRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/{project_id}",
    response_model=ApiResponse[ProjectRead],
    summary="项目详情",
)
def get_project(
    project_id: ProjectId,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ProjectRead]:
    project = ProjectService.get_or_404(db, project_id, current_user.id)
    return ApiResponse(
        data=ProjectRead.model_validate(project),
        request_id=get_request_id(),
    )


@router.put(
    "/{project_id}",
    response_model=ApiResponse[ProjectRead],
    summary="更新项目",
)
def update_project(
    project_id: ProjectId,
    payload: ProjectUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ProjectRead]:
    project = ProjectService.get_or_404(db, project_id, current_user.id)
    project = ProjectService.update(db, project, payload)
    return ApiResponse(
        data=ProjectRead.model_validate(project),
        request_id=get_request_id(),
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除项目",
)
def delete_project(
    project_id: ProjectId,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    project = ProjectService.get_or_404(db, project_id, current_user.id)
    ProjectService.delete(db, project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

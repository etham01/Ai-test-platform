from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi import Path as PathParam
from fastapi.responses import FileResponse

from app.api.deps import DbSession, Pagination, ProjectDep
from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.core.logging import get_request_id
from app.core.paths import PathSecurityError, resolve_within
from app.models.enums import TaskType
from app.schemas.common import ApiResponse, Paginated
from app.schemas.page import (
    PageDetail,
    PageExploreRequest,
    PageRelationList,
    PageScanRequest,
    PageSummary,
)
from app.schemas.task import TaskCreated
from app.services.page_service import PageService
from app.services.task_service import TaskService
from app.tasks.scan_tasks import explore_task, scan_page_task

router = APIRouter(prefix="/projects/{project_id}", tags=["pages"])

PageId = Annotated[int, PathParam(ge=1)]


@router.post(
    "/pages/scan",
    response_model=ApiResponse[TaskCreated],
    summary="采集单个页面（异步）",
)
def scan_page(
    payload: PageScanRequest,
    project: ProjectDep,
    db: DbSession,
) -> ApiResponse[TaskCreated]:
    task = TaskService.create_and_dispatch(
        db,
        project.id,
        TaskType.SCAN,
        lambda task_id: scan_page_task.delay(
            task_id,
            project.id,
            payload.url,
            payload.timeout_seconds,
            payload.wait_after_load_ms,
        ),
    )
    return ApiResponse(
        data=TaskCreated(task_id=task.task_id, task_type=TaskType.SCAN),
        request_id=get_request_id(),
    )


@router.post(
    "/pages/explore",
    response_model=ApiResponse[TaskCreated],
    summary="有限深度多页面探索（异步）",
)
def explore_pages(
    payload: PageExploreRequest,
    project: ProjectDep,
    db: DbSession,
) -> ApiResponse[TaskCreated]:
    config = payload.model_dump()
    config["start_url"] = payload.start_url or project.base_url
    config["browser_type"] = project.browser_type
    task = TaskService.create_and_dispatch(
        db,
        project.id,
        TaskType.EXPLORE,
        lambda task_id: explore_task.delay(task_id, project.id, config),
    )
    return ApiResponse(
        data=TaskCreated(task_id=task.task_id, task_type=TaskType.EXPLORE),
        request_id=get_request_id(),
    )


@router.get(
    "/pages",
    response_model=ApiResponse[Paginated[PageSummary]],
    summary="页面列表",
)
def list_pages(
    project: ProjectDep,
    db: DbSession,
    pagination: Pagination,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(discovered|parsed|failed|blocked)$"),
    ] = None,
) -> ApiResponse[Paginated[PageSummary]]:
    page, page_size = pagination
    items, total = PageService.list_pages(
        db, project.id, page, page_size, status_filter
    )
    return ApiResponse(
        data=Paginated[PageSummary](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        ),
        request_id=get_request_id(),
    )


@router.get(
    "/pages/{page_id}",
    response_model=ApiResponse[PageDetail],
    summary="页面详情与元素",
)
def get_page(
    page_id: PageId,
    project: ProjectDep,
    db: DbSession,
) -> ApiResponse[PageDetail]:
    detail = PageService.get_detail(db, project.id, page_id)
    return ApiResponse(data=detail, request_id=get_request_id())


@router.get(
    "/relations",
    response_model=ApiResponse[PageRelationList],
    summary="页面关系",
)
def list_relations(
    project: ProjectDep,
    db: DbSession,
    limit: int = Query(default=500, ge=1, le=2000),
) -> ApiResponse[PageRelationList]:
    items = PageService.list_relations(db, project.id, limit=limit)
    return ApiResponse(
        data=PageRelationList(items=items, total=len(items)),
        request_id=get_request_id(),
    )


def _file_for_page(
    project_id: int,
    page_id: int,
    db: DbSession,
    attribute: str,
    media_type: str,
) -> FileResponse:
    page = PageService.get_page_or_404(db, project_id, page_id)
    relative = getattr(page, attribute)
    if not relative:
        raise NotFoundError("FILE_NOT_FOUND", "该页面没有对应的文件")
    try:
        path = resolve_within(settings.storage_root, relative)
    except PathSecurityError as exc:
        raise AppError("STORAGE_PATH_INVALID", "文件路径非法", status_code=400) from exc
    if not path.is_file():
        raise NotFoundError("FILE_NOT_FOUND", "文件不存在")
    return FileResponse(path, media_type=media_type)


@router.get(
    "/pages/{page_id}/screenshot",
    summary="页面截图",
    response_class=FileResponse,
)
def page_screenshot(
    page_id: PageId,
    project: ProjectDep,
    db: DbSession,
) -> FileResponse:
    return _file_for_page(
        project.id, page_id, db, "screenshot_path", "image/png"
    )


@router.get(
    "/pages/{page_id}/dom",
    summary="页面 DOM 快照（附件）",
    response_class=FileResponse,
)
def page_dom(
    page_id: PageId,
    project: ProjectDep,
    db: DbSession,
) -> FileResponse:
    response = _file_for_page(
        project.id, page_id, db, "dom_snapshot_path", "text/html"
    )
    response.headers["Content-Disposition"] = (
        f'attachment; filename="page-{page_id}-dom.html"'
    )
    return response

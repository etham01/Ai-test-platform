from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.services.project_service import ProjectService

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession) -> User:
    """Single-user MVP: resolve the seeded demo user.

    Replacing this function with a real authentication dependency is the
    intended extension point for multi-user support.
    """
    user = db.scalar(select(User).where(User.username == "demo"))
    if user is None or not user.is_active:
        raise AppError(
            "DEFAULT_USER_MISSING",
            "默认演示用户不存在，请先执行数据库迁移",
            status_code=500,
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_project_or_404(
    project_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Project:
    return ProjectService.get_or_404(db, project_id, current_user.id)


ProjectDep = Annotated[Project, Depends(get_project_or_404)]


def pagination(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(
        default=settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="每页数量",
    ),
) -> tuple[int, int]:
    return page, page_size


Pagination = Annotated[tuple[int, int], Depends(pagination)]

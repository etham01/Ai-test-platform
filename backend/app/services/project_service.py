from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    @staticmethod
    def create(db: Session, owner_id: int, payload: ProjectCreate) -> Project:
        project = Project(
            owner_id=owner_id,
            name=payload.name,
            description=payload.description,
            base_url=payload.base_url,
            browser_type=payload.browser_type,
            scan_config=payload.scan_config,
            status="active",
        )
        ProjectRepository.create(db, project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_or_404(db: Session, project_id: int, owner_id: int) -> Project:
        project = ProjectRepository.get(db, project_id, owner_id)
        if project is None:
            raise NotFoundError("PROJECT_NOT_FOUND", "项目不存在或无权访问")
        return project

    @staticmethod
    def list(
        db: Session,
        owner_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[Project], int]:
        return ProjectRepository.list_for_owner(db, owner_id, page, page_size, status)

    @staticmethod
    def update(db: Session, project: Project, payload: ProjectUpdate) -> Project:
        data = payload.model_dump(exclude_unset=True)
        for field in ("name", "base_url", "browser_type", "status"):
            value = data.get(field)
            if value is not None:
                setattr(project, field, value)
        if "description" in data:
            project.description = data["description"]
        if "scan_config" in data:
            project.scan_config = data["scan_config"]
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete(db: Session, project: Project) -> None:
        ProjectRepository.soft_delete(db, project)
        db.commit()

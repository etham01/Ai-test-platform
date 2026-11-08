from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.project import Project


class ProjectRepository:
    @staticmethod
    def create(db: Session, project: Project) -> Project:
        db.add(project)
        db.flush()
        return project

    @staticmethod
    def get(db: Session, project_id: int, owner_id: int) -> Project | None:
        return db.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == owner_id,
                Project.deleted_at.is_(None),
            )
        )

    @staticmethod
    def list_for_owner(
        db: Session,
        owner_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[Project], int]:
        conditions = [Project.owner_id == owner_id, Project.deleted_at.is_(None)]
        if status:
            conditions.append(Project.status == status)

        total = db.scalar(select(func.count(Project.id)).where(*conditions)) or 0
        items = db.scalars(
            select(Project)
            .where(*conditions)
            .order_by(Project.created_at.desc(), Project.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), int(total)

    @staticmethod
    def soft_delete(db: Session, project: Project) -> None:
        project.deleted_at = utcnow()
        db.flush()

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.page import WebPage
from app.models.requirement import TestRequirement
from app.schemas.requirement import RequirementCreate, RequirementUpdate


class RequirementService:
    @staticmethod
    def validate_page_ids(
        db: Session, project_id: int, page_ids: list[int] | None
    ) -> list[int]:
        if not page_ids:
            return []
        unique = list(dict.fromkeys(page_ids))
        found = set(
            db.scalars(
                select(WebPage.id).where(
                    WebPage.project_id == project_id,
                    WebPage.id.in_(unique),
                )
            ).all()
        )
        missing = [page_id for page_id in unique if page_id not in found]
        if missing:
            raise AppError(
                "PAGE_NOT_FOUND",
                f"页面不属于当前项目: {missing}",
                status_code=404,
            )
        return unique

    @staticmethod
    def create(
        db: Session,
        project_id: int,
        user_id: int,
        payload: RequirementCreate,
    ) -> TestRequirement:
        page_ids = RequirementService.validate_page_ids(
            db, project_id, payload.related_page_ids
        )
        requirement = TestRequirement(
            project_id=project_id,
            title=payload.title.strip(),
            content=payload.content,
            related_page_ids=page_ids,
            generation_config=payload.generation_config,
            status="draft",
            created_by=user_id,
        )
        db.add(requirement)
        db.commit()
        db.refresh(requirement)
        return requirement

    @staticmethod
    def get_or_404(
        db: Session, requirement_id: int, project_id: int | None = None
    ) -> TestRequirement:
        conditions = [
            TestRequirement.id == requirement_id,
            TestRequirement.deleted_at.is_(None),
        ]
        if project_id is not None:
            conditions.append(TestRequirement.project_id == project_id)
        requirement = db.scalar(select(TestRequirement).where(*conditions))
        if requirement is None:
            raise NotFoundError("REQUIREMENT_NOT_FOUND", "测试需求不存在或无权访问")
        return requirement

    @staticmethod
    def list(
        db: Session,
        project_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[TestRequirement], int]:
        conditions = [
            TestRequirement.project_id == project_id,
            TestRequirement.deleted_at.is_(None),
        ]
        if status:
            conditions.append(TestRequirement.status == status)
        total = db.scalar(select(func.count(TestRequirement.id)).where(*conditions)) or 0
        items = db.scalars(
            select(TestRequirement)
            .where(*conditions)
            .order_by(TestRequirement.created_at.desc(), TestRequirement.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), int(total)

    @staticmethod
    def update(
        db: Session, requirement: TestRequirement, payload: RequirementUpdate
    ) -> TestRequirement:
        data = payload.model_dump(exclude_unset=True)
        if "title" in data and data["title"] is not None:
            requirement.title = data["title"].strip()
        if "content" in data and data["content"] is not None:
            requirement.content = data["content"]
        if "related_page_ids" in data and data["related_page_ids"] is not None:
            requirement.related_page_ids = RequirementService.validate_page_ids(
                db, requirement.project_id, data["related_page_ids"]
            )
        if "generation_config" in data:
            requirement.generation_config = data["generation_config"]
        if "status" in data and data["status"] is not None:
            requirement.status = data["status"]
        db.commit()
        db.refresh(requirement)
        return requirement

    @staticmethod
    def delete(db: Session, requirement: TestRequirement) -> None:
        from app.core.time import utcnow

        requirement.deleted_at = utcnow()
        db.commit()

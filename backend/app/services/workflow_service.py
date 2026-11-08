from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.time import utcnow
from app.models.workflow import Workflow
from app.schemas.ai import WorkflowItem
from app.schemas.workflow import WorkflowUpdate


class WorkflowService:
    @staticmethod
    def get_or_404(db: Session, workflow_id: int, project_id: int | None = None) -> Workflow:
        conditions = [Workflow.id == workflow_id, Workflow.deleted_at.is_(None)]
        if project_id is not None:
            conditions.append(Workflow.project_id == project_id)
        workflow = db.scalar(select(Workflow).where(*conditions))
        if workflow is None:
            raise NotFoundError("WORKFLOW_NOT_FOUND", "业务流程不存在或无权访问")
        return workflow

    @staticmethod
    def list(
        db: Session,
        project_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[Workflow], int]:
        conditions = [Workflow.project_id == project_id, Workflow.deleted_at.is_(None)]
        if status:
            conditions.append(Workflow.status == status)
        total = db.scalar(select(func.count(Workflow.id)).where(*conditions)) or 0
        items = db.scalars(
            select(Workflow)
            .where(*conditions)
            .order_by(Workflow.created_at.desc(), Workflow.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), int(total)

    @staticmethod
    def save_generated(
        db: Session,
        *,
        project_id: int,
        requirement_id: int | None,
        items: list[WorkflowItem],
        generation_record_id: int,
        source: str,
    ) -> list[int]:
        ids: list[int] = []
        for item in items:
            workflow = Workflow(
                project_id=project_id,
                requirement_id=requirement_id,
                name=item.name,
                description=item.description,
                steps=[step.model_dump() for step in item.steps],
                involved_page_ids=item.involved_page_ids,
                uncertainty=item.uncertainty,
                status="inferred",
                source=source,
                generation_record_id=generation_record_id,
            )
            db.add(workflow)
            db.flush()
            ids.append(workflow.id)
        db.commit()
        return ids

    @staticmethod
    def update(db: Session, workflow: Workflow, payload: WorkflowUpdate) -> Workflow:
        data = payload.model_dump(exclude_unset=True)
        for field in ("name", "description", "uncertainty"):
            value = data.get(field)
            if value is not None:
                setattr(workflow, field, value)
        if "steps" in data and data["steps"] is not None:
            workflow.steps = data["steps"]
        if "involved_page_ids" in data and data["involved_page_ids"] is not None:
            workflow.involved_page_ids = data["involved_page_ids"]
        if "status" in data and data["status"] is not None:
            workflow.status = data["status"]
        db.commit()
        db.refresh(workflow)
        return workflow

    @staticmethod
    def delete(db: Session, workflow: Workflow) -> None:
        workflow.deleted_at = utcnow()
        db.commit()

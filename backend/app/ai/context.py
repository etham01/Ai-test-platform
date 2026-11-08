from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.page import PageElement, PageRelation, WebPage
from app.models.project import Project
from app.models.requirement import TestRequirement
from app.models.workflow import Workflow

MAX_PAGES = 20
MAX_ELEMENTS = 30
MAX_RELATIONS = 200


def _page_dict(db: Session, page: WebPage) -> dict[str, Any]:
    elements = db.scalars(
        select(PageElement)
        .where(PageElement.page_id == page.id)
        .order_by(PageElement.id.asc())
        .limit(MAX_ELEMENTS)
    ).all()
    return {
        "id": page.id,
        "url": page.url,
        "title": page.title,
        "depth": page.depth,
        "status": page.status,
        "text_summary": (page.text_summary or "")[:1500],
        "elements": [
            {
                "element_type": element.element_type,
                "tag": element.tag,
                "role": element.role,
                "accessible_name": element.accessible_name,
                "label": element.label,
                "placeholder": element.placeholder,
                "text": element.text,
                "input_type": element.input_type,
                "href": element.href,
                "selector_candidates": element.selector_candidates,
                "is_sensitive": element.is_sensitive,
            }
            for element in elements
        ],
    }


def build_context(
    db: Session,
    project: Project,
    *,
    requirement: TestRequirement | None = None,
    page_ids: list[int] | None = None,
    include_workflows: bool = True,
) -> dict[str, Any]:
    conditions = [WebPage.project_id == project.id]
    if page_ids:
        conditions.append(WebPage.id.in_(page_ids))
    pages = db.scalars(
        select(WebPage)
        .where(*conditions)
        .order_by(WebPage.depth.asc(), WebPage.id.asc())
        .limit(MAX_PAGES)
    ).all()

    if page_ids:
        found = {page.id for page in pages}
        missing = [page_id for page_id in page_ids if page_id not in found]
        if missing:
            raise AppError(
                "PAGE_NOT_FOUND",
                f"页面不属于当前项目: {missing}",
                status_code=404,
            )

    relations = db.scalars(
        select(PageRelation)
        .where(PageRelation.project_id == project.id)
        .order_by(PageRelation.id.asc())
        .limit(MAX_RELATIONS)
    ).all()

    workflows = []
    if include_workflows:
        workflow_query = select(Workflow).where(
            Workflow.project_id == project.id,
            Workflow.deleted_at.is_(None),
        )
        if requirement is not None:
            workflow_query = workflow_query.where(
                Workflow.requirement_id == requirement.id
            )
        workflows = list(
            db.scalars(workflow_query.order_by(Workflow.id.asc()).limit(10)).all()
        )

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "base_url": project.base_url,
        },
        "requirement": (
            {
                "id": requirement.id,
                "title": requirement.title,
                "content": requirement.content[:8000],
                "related_page_ids": requirement.related_page_ids or [],
            }
            if requirement is not None
            else None
        ),
        "pages": [_page_dict(db, page) for page in pages],
        "relations": [
            {
                "from_page_id": relation.from_page_id,
                "to_page_id": relation.to_page_id,
                "target_url": relation.target_url,
                "relation_type": relation.relation_type,
                "source": relation.source,
                "confidence": relation.confidence,
            }
            for relation in relations
        ],
        "workflows": [
            {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "steps": workflow.steps,
                "involved_page_ids": workflow.involved_page_ids,
                "status": workflow.status,
                "source": workflow.source,
            }
            for workflow in workflows
        ],
    }


def context_summary(context: dict[str, Any]) -> str:
    requirement = context.get("requirement") or {}
    return (
        f"pages={len(context.get('pages', []))}; "
        f"relations={len(context.get('relations', []))}; "
        f"requirement={requirement.get('title', '无')}"
    )

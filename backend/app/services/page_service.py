from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.browser.site_explorer import ExploredPage
from app.browser.url_policy import normalize_url
from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.paths import relative_posix
from app.core.time import utcnow
from app.models.page import PageElement, PageRelation, WebPage
from app.schemas.page import PageDetail, PageElementRead, PageRelationRead, PageSummary


def url_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class PageService:
    @staticmethod
    def _artifacts(
        project_id: int, page_id: int, parsed
    ) -> tuple[str | None, str | None]:
        base = settings.storage_root / "projects" / str(project_id) / "pages" / str(page_id)
        base.mkdir(parents=True, exist_ok=True)
        dom_path = base / "dom.html"
        dom_path.write_text(parsed.dom_html, encoding="utf-8")
        screenshot_path: Path | None = None
        if parsed.screenshot_png:
            screenshot_path = base / "screenshot.png"
            screenshot_path.write_bytes(parsed.screenshot_png)
        return (
            relative_posix(dom_path),
            relative_posix(screenshot_path) if screenshot_path else None,
        )

    @staticmethod
    def _find_page_id(db: Session, project_id: int, url: str | None) -> int | None:
        if not url:
            return None
        try:
            normalized = normalize_url(url)
        except Exception:
            return None
        page = db.scalar(
            select(WebPage).where(
                WebPage.project_id == project_id,
                WebPage.url_hash == url_hash(normalized),
            )
        )
        return page.id if page else None

    @staticmethod
    def upsert_page(
        db: Session,
        project_id: int,
        result: ExploredPage,
        *,
        discovered_from_page_id: int | None = None,
    ) -> WebPage:
        normalized = result.normalized_url
        digest = url_hash(normalized)
        page = db.scalar(
            select(WebPage).where(
                WebPage.project_id == project_id,
                WebPage.url_hash == digest,
            )
        )
        if page is None:
            page = WebPage(
                project_id=project_id,
                url=result.final_url or result.requested_url,
                normalized_url=normalized,
                url_hash=digest,
                depth=result.depth,
                status=result.status,
                source=result.source,
                discovered_from_page_id=discovered_from_page_id,
            )
            db.add(page)
            db.flush()
        else:
            page.url = result.final_url or result.requested_url
            page.normalized_url = normalized
            page.depth = min(page.depth, result.depth)
            page.status = result.status
            page.source = result.source
            page.error_message = None

        page.title = result.parsed.title if result.parsed else None
        page.http_status = result.parsed.http_status if result.parsed else None
        page.content_type = result.parsed.content_type if result.parsed else None
        page.text_summary = result.parsed.text_summary if result.parsed else None
        page.fetched_at = utcnow()
        page.error_message = result.error

        db.execute(delete(PageElement).where(PageElement.page_id == page.id))
        db.execute(
            delete(PageRelation).where(
                PageRelation.from_page_id == page.id,
                PageRelation.source.like("observed_%"),
            )
        )

        if result.parsed is not None:
            dom_path, screenshot_path = PageService._artifacts(
                project_id, page.id, result.parsed
            )
            page.dom_snapshot_path = dom_path
            page.screenshot_path = screenshot_path
            now = utcnow()
            for element in result.parsed.elements:
                db.add(
                    PageElement(
                        project_id=project_id,
                        page_id=page.id,
                        element_type=element.element_type,
                        tag=element.tag,
                        role=element.role,
                        accessible_name=element.accessible_name,
                        label=element.label,
                        placeholder=element.placeholder,
                        text=element.text,
                        element_id=element.element_id,
                        name=element.name,
                        input_type=element.input_type,
                        href=element.href,
                        selector_candidates=element.selector_candidates,
                        is_sensitive=element.is_sensitive,
                        attributes=element.attributes,
                        created_at=now,
                    )
                )

        seen_relations: set[tuple[str | None, str]] = set()
        for link in result.links:
            key = (link.href, "link")
            if key in seen_relations:
                continue
            seen_relations.add(key)
            db.add(
                PageRelation(
                    project_id=project_id,
                    from_page_id=page.id,
                    to_page_id=PageService._find_page_id(db, project_id, link.href),
                    target_url=link.href,
                    relation_type="link",
                    source="observed_link",
                    confidence=1.0,
                    evidence={"href": link.href, "text": link.text},
                    created_at=utcnow(),
                )
            )
        for form in result.form_actions:
            key = (form.action, "form_action")
            if key in seen_relations:
                continue
            seen_relations.add(key)
            db.add(
                PageRelation(
                    project_id=project_id,
                    from_page_id=page.id,
                    to_page_id=PageService._find_page_id(db, project_id, form.action),
                    target_url=form.action,
                    relation_type="form_action",
                    source="observed_form_action",
                    confidence=1.0,
                    evidence={
                        "action": form.action,
                        "method": form.method,
                        "fields": form.fields,
                    },
                    created_at=utcnow(),
                )
            )

        db.commit()
        db.refresh(page)
        return page

    @staticmethod
    def resolve_relation_targets(db: Session, project_id: int) -> int:
        relations = db.scalars(
            select(PageRelation).where(
                PageRelation.project_id == project_id,
                PageRelation.to_page_id.is_(None),
                PageRelation.target_url.is_not(None),
            )
        ).all()
        updated = 0
        for relation in relations:
            target_id = PageService._find_page_id(
                db, project_id, relation.target_url
            )
            if target_id is not None:
                relation.to_page_id = target_id
                updated += 1
        db.commit()
        return updated

    @staticmethod
    def get_page_or_404(db: Session, project_id: int, page_id: int) -> WebPage:
        page = db.scalar(
            select(WebPage).where(
                WebPage.id == page_id, WebPage.project_id == project_id
            )
        )
        if page is None:
            raise NotFoundError("PAGE_NOT_FOUND", "页面不存在或不属于当前项目")
        return page

    @staticmethod
    def list_pages(
        db: Session,
        project_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[PageSummary], int]:
        conditions = [WebPage.project_id == project_id]
        if status:
            conditions.append(WebPage.status == status)
        total = db.scalar(select(func.count(WebPage.id)).where(*conditions)) or 0
        pages = db.scalars(
            select(WebPage)
            .where(*conditions)
            .order_by(WebPage.depth.asc(), WebPage.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        summaries = [
            PageService._summary(
                db,
                item,
                int(
                    db.scalar(
                        select(func.count(PageElement.id)).where(
                            PageElement.page_id == item.id
                        )
                    )
                    or 0
                ),
            )
            for item in pages
        ]
        return summaries, int(total)

    @staticmethod
    def _summary(db: Session, page: WebPage, element_count: int) -> PageSummary:
        return PageSummary(
            id=page.id,
            url=page.url,
            title=page.title,
            depth=page.depth,
            status=page.status,
            http_status=page.http_status,
            source=page.source,
            element_count=element_count,
            error_message=page.error_message,
            created_at=page.created_at,
            updated_at=page.updated_at,
        )

    @staticmethod
    def get_detail(db: Session, project_id: int, page_id: int) -> PageDetail:
        page = PageService.get_page_or_404(db, project_id, page_id)
        elements = db.scalars(
            select(PageElement)
            .where(PageElement.page_id == page.id)
            .order_by(PageElement.id.asc())
        ).all()
        return PageDetail(
            **PageService._summary(db, page, len(elements)).model_dump(),
            normalized_url=page.normalized_url,
            content_type=page.content_type,
            text_summary=page.text_summary,
            screenshot_url=(
                f"/api/v1/projects/{project_id}/pages/{page.id}/screenshot"
                if page.screenshot_path
                else None
            ),
            dom_url=(
                f"/api/v1/projects/{project_id}/pages/{page.id}/dom"
                if page.dom_snapshot_path
                else None
            ),
            elements=[PageElementRead.model_validate(item) for item in elements],
        )

    @staticmethod
    def list_relations(
        db: Session, project_id: int, limit: int = 500
    ) -> list[PageRelationRead]:
        relations = db.scalars(
            select(PageRelation)
            .where(PageRelation.project_id == project_id)
            .order_by(PageRelation.id.asc())
            .limit(limit)
        ).all()
        return [PageRelationRead.model_validate(item) for item in relations]

    @staticmethod
    def count_relations(db: Session, project_id: int) -> int:
        return int(
            db.scalar(
                select(func.count(PageRelation.id)).where(
                    PageRelation.project_id == project_id
                )
            )
            or 0
        )

    @staticmethod
    def count_pages(db: Session, project_id: int) -> int:
        return int(
            db.scalar(
                select(func.count(WebPage.id)).where(
                    WebPage.project_id == project_id
                )
            )
            or 0
        )


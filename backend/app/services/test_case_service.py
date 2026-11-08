from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.time import utcnow
from app.models.test_case import TestCase
from app.schemas.ai import CaseItem
from app.schemas.test_case import TestCaseUpdate


class TestCaseService:
    @staticmethod
    def get_or_404(
        db: Session, case_id: int, project_id: int | None = None
    ) -> TestCase:
        conditions = [TestCase.id == case_id, TestCase.deleted_at.is_(None)]
        if project_id is not None:
            conditions.append(TestCase.project_id == project_id)
        case = db.scalar(select(TestCase).where(*conditions))
        if case is None:
            raise NotFoundError("CASE_NOT_FOUND", "测试用例不存在或无权访问")
        return case

    @staticmethod
    def list(
        db: Session,
        project_id: int,
        page: int,
        page_size: int,
        *,
        requirement_id: int | None = None,
        status: str | None = None,
        priority: str | None = None,
    ) -> tuple[list[TestCase], int]:
        conditions = [
            TestCase.project_id == project_id,
            TestCase.deleted_at.is_(None),
        ]
        if requirement_id is not None:
            conditions.append(TestCase.requirement_id == requirement_id)
        if status:
            conditions.append(TestCase.status == status)
        if priority:
            conditions.append(TestCase.priority == priority)
        total = db.scalar(select(func.count(TestCase.id)).where(*conditions)) or 0
        items = db.scalars(
            select(TestCase)
            .where(*conditions)
            .order_by(TestCase.created_at.desc(), TestCase.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), int(total)

    @staticmethod
    def _unique_case_code(base: str, used: set[str]) -> str:
        if base not in used:
            return base
        for suffix in range(2, 1000):
            candidate = f"{base[:56]}-R{suffix}"
            if candidate not in used:
                return candidate
        raise RuntimeError("无法生成唯一 case_code")

    @staticmethod
    def save_generated(
        db: Session,
        *,
        project_id: int,
        requirement_id: int | None,
        items: list[CaseItem],
        generation_record_id: int,
        source: str,
    ) -> list[int]:
        existing = set(
            db.scalars(
                select(TestCase.case_code).where(TestCase.project_id == project_id)
            ).all()
        )
        ids: list[int] = []
        for item in items:
            code = TestCaseService._unique_case_code(item.case_code, existing)
            existing.add(code)
            needs_review = any(
                assertion.source == "model_inference"
                for assertion in item.assertions
            )
            case = TestCase(
                project_id=project_id,
                requirement_id=requirement_id,
                case_code=code,
                title=item.title,
                module=item.module,
                priority=item.priority,
                preconditions=item.preconditions,
                related_page_ids=item.related_page_ids,
                steps=[step.model_dump() for step in item.steps],
                test_data=item.test_data,
                expected_result=item.expected_result,
                assertions=[assertion.model_dump() for assertion in item.assertions],
                assumptions=item.assumptions,
                status="needs_review" if needs_review else "draft",
                generation_source=source,
                generation_record_id=generation_record_id,
            )
            db.add(case)
            db.flush()
            ids.append(case.id)
        db.commit()
        return ids

    @staticmethod
    def update(db: Session, case: TestCase, payload: TestCaseUpdate) -> TestCase:
        data = payload.model_dump(exclude_unset=True)
        for field in (
            "title",
            "module",
            "priority",
            "preconditions",
            "related_page_ids",
            "steps",
            "test_data",
            "expected_result",
            "assertions",
            "assumptions",
            "status",
        ):
            if field in data and data[field] is not None:
                setattr(case, field, data[field])
        db.commit()
        db.refresh(case)
        return case

    @staticmethod
    def delete(db: Session, case: TestCase) -> None:
        case.deleted_at = utcnow()
        db.commit()

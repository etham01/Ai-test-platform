from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.paths import safe_filename
from app.core.time import utcnow
from app.execution.script_validator import validate_script
from app.models.test_script import TestScript
from app.schemas.script import ScriptDetail, ScriptSummary


class ScriptService:
    @staticmethod
    def get_or_404(
        db: Session, script_id: int, project_id: int | None = None
    ) -> TestScript:
        conditions = [TestScript.id == script_id, TestScript.deleted_at.is_(None)]
        if project_id is not None:
            conditions.append(TestScript.project_id == project_id)
        script = db.scalar(select(TestScript).where(*conditions))
        if script is None:
            raise NotFoundError("SCRIPT_NOT_FOUND", "测试脚本不存在或无权访问")
        return script

    @staticmethod
    def list(
        db: Session,
        project_id: int,
        page: int,
        page_size: int,
        *,
        test_case_id: int | None = None,
        status: str | None = None,
    ) -> tuple[list[TestScript], int]:
        conditions = [
            TestScript.project_id == project_id,
            TestScript.deleted_at.is_(None),
        ]
        if test_case_id is not None:
            conditions.append(TestScript.test_case_id == test_case_id)
        if status:
            conditions.append(TestScript.status == status)
        total = db.scalar(select(func.count(TestScript.id)).where(*conditions)) or 0
        items = db.scalars(
            select(TestScript)
            .where(*conditions)
            .order_by(TestScript.created_at.desc(), TestScript.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), int(total)

    @staticmethod
    def _next_version(db: Session, case_id: int) -> int:
        current = db.scalar(
            select(func.max(TestScript.version)).where(
                TestScript.test_case_id == case_id
            )
        )
        return int(current or 0) + 1

    @staticmethod
    def create_version(
        db: Session,
        *,
        project_id: int,
        test_case_id: int,
        filename: str,
        content: str,
        generation_source: str,
        generation_record_id: int | None,
    ) -> TestScript:
        version = ScriptService._next_version(db, test_case_id)
        safe = safe_filename(filename, default="test_script.py")
        if not safe.endswith(".py"):
            safe += ".py"
        stem = Path(safe).stem
        if not stem.startswith("test_"):
            stem = f"test_{stem}"
        final_name = f"{stem}_v{version}.py"
        report = validate_script(content, filename=final_name)
        status = "validated" if report["ok"] else "rejected"
        script = TestScript(
            project_id=project_id,
            test_case_id=test_case_id,
            version=version,
            filename=final_name,
            content=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            status=status,
            validation_report=report,
            generation_source=generation_source,
            generation_record_id=generation_record_id,
            updated_at=utcnow(),
        )
        db.add(script)
        db.commit()
        db.refresh(script)
        return script

    @staticmethod
    def update_content(db: Session, script: TestScript, content: str) -> TestScript:
        return ScriptService.create_version(
            db,
            project_id=script.project_id,
            test_case_id=script.test_case_id,
            filename=script.filename,
            content=content,
            generation_source="user",
            generation_record_id=None,
        )

    @staticmethod
    def revalidate(db: Session, script: TestScript) -> TestScript:
        report = validate_script(script.content, filename=script.filename)
        script.validation_report = report
        script.status = "validated" if report["ok"] else "rejected"
        script.updated_at = utcnow()
        db.commit()
        db.refresh(script)
        return script

    @staticmethod
    def to_summary(script: TestScript) -> ScriptSummary:
        return ScriptSummary.model_validate(script)

    @staticmethod
    def to_detail(script: TestScript) -> ScriptDetail:
        return ScriptDetail.model_validate(script)

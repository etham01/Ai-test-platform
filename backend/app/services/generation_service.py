from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.output_parser import summarize_output
from app.ai.providers.base import LLMResult
from app.core.config import settings
from app.core.paths import relative_posix
from app.core.time import utcnow
from app.models.generation import GenerationRecord


class GenerationService:
    @staticmethod
    def _write_raw(project_id: int, content: str) -> str | None:
        if not content:
            return None
        directory = settings.storage_root / "projects" / str(project_id) / "generations"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{uuid4().hex}.txt"
        path.write_text(content, encoding="utf-8")
        return relative_posix(path)

    @staticmethod
    def record_success(
        db: Session,
        *,
        project_id: int,
        task_type: str,
        result: LLMResult,
        input_summary: str,
    ) -> GenerationRecord:
        record = GenerationRecord(
            project_id=project_id,
            task_type=task_type,
            prompt_version=result.prompt_version,
            provider=result.provider,
            model=result.model,
            is_mock=result.is_mock,
            input_summary=input_summary[:8000],
            output_summary=summarize_output(result.content),
            raw_response_path=GenerationService._write_raw(project_id, result.content),
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            duration_ms=result.duration_ms,
            status="succeeded",
            created_at=utcnow(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def record_failure(
        db: Session,
        *,
        project_id: int,
        task_type: str,
        prompt_version: str,
        provider: str,
        model: str,
        is_mock: bool,
        input_summary: str,
        error: str,
        duration_ms: int | None = None,
    ) -> GenerationRecord:
        record = GenerationRecord(
            project_id=project_id,
            task_type=task_type,
            prompt_version=prompt_version,
            provider=provider,
            model=model,
            is_mock=is_mock,
            input_summary=input_summary[:8000],
            output_summary=None,
            raw_response_path=None,
            duration_ms=duration_ms,
            status="failed",
            error=error[:4000],
            created_at=utcnow(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def list_records(
        db: Session, project_id: int, limit: int = 50
    ) -> list[GenerationRecord]:
        return list(
            db.scalars(
                select(GenerationRecord)
                .where(GenerationRecord.project_id == project_id)
                .order_by(GenerationRecord.id.desc())
                .limit(limit)
            ).all()
        )

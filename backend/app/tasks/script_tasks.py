from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from app.ai.context import build_context
from app.ai.providers.base import LLMError
from app.ai.service import generate_structured
from app.models.project import Project
from app.models.test_case import TestCase
from app.schemas.ai import ScriptGenerationResult
from app.services.generation_service import GenerationService
from app.services.llm_config_service import LLMConfigService
from app.services.script_service import ScriptService
from app.tasks.celery_app import celery_app
from app.tasks.task_utils import (
    add_log,
    get_task,
    mark_failed,
    mark_running,
    mark_succeeded,
    task_session,
)

logger = logging.getLogger(__name__)


def _case_payload(case: TestCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "case_code": case.case_code,
        "title": case.title,
        "module": case.module,
        "priority": case.priority,
        "preconditions": case.preconditions,
        "related_page_ids": case.related_page_ids,
        "steps": case.steps,
        "test_data": case.test_data,
        "expected_result": case.expected_result,
        "assertions": case.assertions,
        "assumptions": case.assumptions,
    }


@celery_app.task(bind=True, name="smarttest.ai.script_generation")
def generate_scripts_task(
    self,
    task_id: str,
    project_id: int,
    test_case_ids: list[int],
) -> dict[str, Any]:
    with task_session() as db:
        task = get_task(db, task_id)
        if task is None:
            return {"ok": False}
        provider = None
        try:
            project = db.get(Project, project_id)
            if project is None or project.deleted_at is not None:
                mark_failed(db, task, "项目不存在或已删除", "项目不可用")
                return {"ok": False}

            cases = list(
                db.scalars(
                    select(TestCase).where(
                        TestCase.project_id == project_id,
                        TestCase.id.in_(test_case_ids),
                        TestCase.deleted_at.is_(None),
                    )
                ).all()
            )
            if not cases:
                mark_failed(db, task, "没有找到可用测试用例", "用例不存在")
                return {"ok": False}

            mark_running(db, task, "调用模型生成测试脚本", 10)
            add_log(db, task, f"准备为 {len(cases)} 条用例生成脚本", "info")
            provider = LLMConfigService.build_provider(db, project_id)
            script_ids: list[int] = []
            rejected: list[dict[str, Any]] = []
            warnings: list[str] = []

            for index, case in enumerate(cases, start=1):
                context = build_context(
                    db,
                    project,
                    page_ids=case.related_page_ids or [],
                    include_workflows=False,
                )
                context["case"] = _case_payload(case)
                validated, result = generate_structured(
                    provider,
                    "script_generation",
                    context,
                    ScriptGenerationResult,
                )
                record = GenerationService.record_success(
                    db,
                    project_id=project_id,
                    task_type="script_generation",
                    result=result,
                    input_summary=f"case_id={case.id}; case_code={case.case_code}",
                )
                script = ScriptService.create_version(
                    db,
                    project_id=project_id,
                    test_case_id=case.id,
                    filename=validated.filename,
                    content=validated.content,
                    generation_source="mock" if result.is_mock else "llm",
                    generation_record_id=record.id,
                )
                script_ids.append(script.id)
                if script.status != "validated":
                    rejected.append(
                        {
                            "script_id": script.id,
                            "case_id": case.id,
                            "issues": (script.validation_report or {}).get(
                                "issues", []
                            ),
                        }
                    )
                warnings.extend(validated.assumptions)
                add_log(
                    db,
                    task,
                    f"[{index}/{len(cases)}] {case.case_code} -> {script.filename} "
                    f"({script.status})",
                    "info" if script.status == "validated" else "warning",
                )

            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_succeeded(
                    db,
                    fresh,
                    {
                        "script_ids": script_ids,
                        "rejected": rejected,
                        "warnings": warnings,
                    },
                    f"生成 {len(script_ids)} 个脚本，{len(rejected)} 个需修正",
                )
                add_log(db, fresh, f"脚本生成完成：{len(script_ids)} 个", "info")
            return {"ok": True, "script_ids": script_ids, "rejected": rejected}
        except LLMError as exc:
            db.rollback()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{exc.code}: {exc.message}", "脚本生成失败")
                add_log(db, fresh, f"脚本生成失败：{exc.message}", "error")
            return {"ok": False, "error": exc.message}
        except Exception as exc:  # pragma: no cover - defensive worker path
            logger.exception("Script generation failed")
            db.rollback()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{type(exc).__name__}: {exc}", "脚本生成失败")
                add_log(db, fresh, "脚本生成发生异常，详见执行日志", "error")
            raise
        finally:
            if provider is not None:
                provider.close()

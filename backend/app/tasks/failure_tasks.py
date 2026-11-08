from __future__ import annotations

import logging

from app.ai.context import build_context
from app.ai.providers.base import LLMError
from app.ai.service import generate_structured
from app.models.execution import TestExecution, TestResult
from app.models.project import Project
from app.models.test_case import TestCase
from app.models.test_script import TestScript
from app.schemas.ai import FailureAnalysisResult
from app.services.generation_service import GenerationService
from app.services.llm_config_service import LLMConfigService
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


@celery_app.task(bind=True, name="smarttest.ai.failure_analysis")
def analyze_failure_task(
    self,
    task_id: str,
    project_id: int,
    execution_id: int,
    result_id: int,
) -> dict[str, object]:
    with task_session() as db:
        task = get_task(db, task_id)
        if task is None:
            return {"ok": False}
        provider = None
        try:
            project = db.get(Project, project_id)
            execution = db.get(TestExecution, execution_id)
            result = db.get(TestResult, result_id)
            if (
                project is None
                or execution is None
                or result is None
                or execution.project_id != project_id
                or result.execution_id != execution_id
            ):
                mark_failed(db, task, "执行结果不存在或不属于当前项目", "结果不可用")
                return {"ok": False}
            if result.status not in {"failed", "error"}:
                mark_failed(db, task, "只有失败/错误结果可以分析", "结果状态不支持")
                return {"ok": False}

            case = db.get(TestCase, result.test_case_id) if result.test_case_id else None
            script = db.get(TestScript, result.script_id) if result.script_id else None
            context = build_context(
                db,
                project,
                page_ids=(case.related_page_ids or []) if case else [],
                include_workflows=False,
            )
            payload = {
                "result": {
                    "test_name": result.test_name,
                    "status": result.status,
                    "failure_message": result.failure_message,
                    "traceback": result.traceback,
                    "duration_ms": result.duration_ms,
                },
                "case": (
                    {
                        "id": case.id,
                        "case_code": case.case_code,
                        "title": case.title,
                        "steps": case.steps,
                        "assertions": case.assertions,
                        "expected_result": case.expected_result,
                    }
                    if case
                    else None
                ),
                "script": (
                    {
                        "id": script.id,
                        "filename": script.filename,
                        "content": script.content[:10000],
                    }
                    if script
                    else None
                ),
                "pages": context.get("pages", []),
            }

            mark_running(db, task, "调用模型分析失败原因", 10)
            add_log(db, task, f"分析失败结果 {result.id} ({result.test_name})", "info")
            provider = LLMConfigService.build_provider(db, project_id)
            validated, llm_result = generate_structured(
                provider,
                "failure_analysis",
                payload,
                FailureAnalysisResult,
            )
            record = GenerationService.record_success(
                db,
                project_id=project_id,
                task_type="failure_analysis",
                result=llm_result,
                input_summary=f"result_id={result.id}; test={result.test_name}",
            )
            result.failure_analysis = {
                **validated.model_dump(),
                "provider": llm_result.provider,
                "model": llm_result.model,
                "is_mock": llm_result.is_mock,
            }
            result.analysis_generation_record_id = record.id
            db.commit()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_succeeded(
                    db,
                    fresh,
                    {
                        "result_id": result.id,
                        "generation_record_id": record.id,
                        "is_mock": llm_result.is_mock,
                    },
                    "失败分析完成",
                )
                add_log(db, fresh, "失败分析完成", "info")
            return {"ok": True, "result_id": result.id}
        except LLMError as exc:
            db.rollback()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{exc.code}: {exc.message}", "失败分析失败")
                add_log(db, fresh, f"失败分析失败：{exc.message}", "error")
            return {"ok": False, "error": exc.message}
        except Exception as exc:  # pragma: no cover - defensive worker path
            logger.exception("Failure analysis failed")
            db.rollback()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{type(exc).__name__}: {exc}", "失败分析失败")
                add_log(db, fresh, "失败分析发生异常，详见执行日志", "error")
            raise
        finally:
            if provider is not None:
                provider.close()

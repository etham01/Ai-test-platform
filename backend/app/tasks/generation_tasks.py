from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from app.ai.context import build_context, context_summary
from app.ai.providers.base import LLMError
from app.ai.service import generate_structured
from app.models.page import WebPage
from app.models.project import Project
from app.schemas.ai import CaseGenerationResult, WorkflowAnalysisResult
from app.services.generation_service import GenerationService
from app.services.llm_config_service import LLMConfigService
from app.services.requirement_service import RequirementService
from app.services.test_case_service import TestCaseService
from app.services.workflow_service import WorkflowService
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


def _valid_page_ids(db, project_id: int) -> set[int]:
    return set(
        db.scalars(
            select(WebPage.id).where(WebPage.project_id == project_id)
        ).all()
    )


def _record_failure(
    db,
    *,
    project_id: int,
    task_type: str,
    context: dict[str, Any],
    error: str,
) -> None:
    config = LLMConfigService.read(db, project_id)
    GenerationService.record_failure(
        db,
        project_id=project_id,
        task_type=task_type,
        prompt_version="v1",
        provider=config.provider,
        model=config.model,
        is_mock=config.is_mock,
        input_summary=context_summary(context) if context else "",
        error=error,
    )


@celery_app.task(bind=True, name="smarttest.ai.workflow_analysis")
def analyze_workflows_task(
    self,
    task_id: str,
    project_id: int,
    requirement_id: int | None = None,
    page_ids: list[int] | None = None,
) -> dict[str, Any]:
    with task_session() as db:
        task = get_task(db, task_id)
        if task is None:
            return {"ok": False}
        provider = None
        context: dict[str, Any] = {}
        try:
            project = db.get(Project, project_id)
            if project is None or project.deleted_at is not None:
                mark_failed(db, task, "项目不存在或已删除", "项目不可用")
                return {"ok": False}
            requirement = (
                RequirementService.get_or_404(db, requirement_id, project_id)
                if requirement_id is not None
                else None
            )
            context = build_context(
                db,
                project,
                requirement=requirement,
                page_ids=page_ids or [],
            )
            if not context.get("pages"):
                mark_failed(db, task, "当前项目还没有已采集页面", "缺少页面")
                return {"ok": False}

            mark_running(db, task, "调用模型分析业务流程", 10)
            add_log(db, task, f"生成上下文：{context_summary(context)}", "info")
            provider = LLMConfigService.build_provider(db, project_id)
            validated, result = generate_structured(
                provider,
                "workflow_analysis",
                context,
                WorkflowAnalysisResult,
            )
            if not validated.workflows:
                raise LLMError("LLM_EMPTY_OUTPUT", "模型没有返回业务流程")

            valid_ids = _valid_page_ids(db, project_id)
            warnings: list[str] = []
            for workflow in validated.workflows:
                filtered = [
                    page_id
                    for page_id in workflow.involved_page_ids
                    if page_id in valid_ids
                ]
                if len(filtered) != len(workflow.involved_page_ids):
                    warnings.append("已移除不属于当前项目的 involved_page_ids")
                workflow.involved_page_ids = filtered
                for step in workflow.steps:
                    if step.page_id is not None and step.page_id not in valid_ids:
                        step.page_id = None
                        warnings.append("已清空不属于当前项目的步骤 page_id")

            record = GenerationService.record_success(
                db,
                project_id=project_id,
                task_type="workflow_analysis",
                result=result,
                input_summary=context_summary(context),
            )
            workflow_ids = WorkflowService.save_generated(
                db,
                project_id=project_id,
                requirement_id=requirement_id,
                items=validated.workflows,
                generation_record_id=record.id,
                source="mock" if result.is_mock else "llm",
            )
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_succeeded(
                    db,
                    fresh,
                    {
                        "workflow_ids": workflow_ids,
                        "warnings": warnings,
                        "generation_record_id": record.id,
                        "is_mock": result.is_mock,
                    },
                    f"生成 {len(workflow_ids)} 个业务流程",
                )
                add_log(db, fresh, f"生成 {len(workflow_ids)} 个业务流程", "info")
            return {"ok": True, "workflow_ids": workflow_ids}
        except LLMError as exc:
            db.rollback()
            _record_failure(
                db,
                project_id=project_id,
                task_type="workflow_analysis",
                context=context,
                error=f"{exc.code}: {exc.message} {exc.details or ''}".strip(),
            )
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{exc.code}: {exc.message}", "流程分析失败")
                add_log(db, fresh, f"流程分析失败：{exc.message}", "error")
            return {"ok": False, "error": exc.message}
        except Exception as exc:  # pragma: no cover - defensive worker path
            logger.exception("Workflow analysis failed")
            db.rollback()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{type(exc).__name__}: {exc}", "流程分析失败")
                add_log(db, fresh, "流程分析发生异常，详见执行日志", "error")
            raise
        finally:
            if provider is not None:
                provider.close()


@celery_app.task(bind=True, name="smarttest.ai.case_generation")
def generate_cases_task(
    self,
    task_id: str,
    project_id: int,
    requirement_id: int,
    page_ids: list[int] | None = None,
    max_cases: int = 5,
    include_workflow_ids: list[int] | None = None,
) -> dict[str, Any]:
    with task_session() as db:
        task = get_task(db, task_id)
        if task is None:
            return {"ok": False}
        provider = None
        context: dict[str, Any] = {}
        try:
            project = db.get(Project, project_id)
            if project is None or project.deleted_at is not None:
                mark_failed(db, task, "项目不存在或已删除", "项目不可用")
                return {"ok": False}
            requirement = RequirementService.get_or_404(
                db, requirement_id, project_id
            )
            selected_ids = page_ids or requirement.related_page_ids or []
            context = build_context(
                db,
                project,
                requirement=requirement,
                page_ids=selected_ids,
            )
            if not context.get("pages"):
                mark_failed(db, task, "当前项目还没有已采集页面", "缺少页面")
                return {"ok": False}
            context["max_cases"] = max(1, min(10, max_cases))
            if include_workflow_ids:
                context["requested_workflow_ids"] = include_workflow_ids

            mark_running(db, task, "调用模型生成测试用例", 10)
            add_log(db, task, f"生成上下文：{context_summary(context)}", "info")
            provider = LLMConfigService.build_provider(db, project_id)
            validated, result = generate_structured(
                provider,
                "case_generation",
                context,
                CaseGenerationResult,
            )
            if not validated.cases:
                raise LLMError("LLM_EMPTY_OUTPUT", "模型没有返回测试用例")

            valid_ids = _valid_page_ids(db, project_id)
            warnings: list[str] = []
            for case in validated.cases:
                filtered_related = [
                    page_id
                    for page_id in case.related_page_ids
                    if page_id in valid_ids
                ]
                if len(filtered_related) != len(case.related_page_ids):
                    warnings.append(f"{case.case_code}: 已移除无效 related_page_ids")
                case.related_page_ids = filtered_related
                for step in case.steps:
                    if step.page_reference and step.page_reference.isdigit():
                        page_id = int(step.page_reference)
                        if page_id not in valid_ids:
                            step.page_reference = None
                            warnings.append(
                                f"{case.case_code}: 已清空无效步骤页面引用 {page_id}"
                            )

            record = GenerationService.record_success(
                db,
                project_id=project_id,
                task_type="case_generation",
                result=result,
                input_summary=context_summary(context),
            )
            case_ids = TestCaseService.save_generated(
                db,
                project_id=project_id,
                requirement_id=requirement_id,
                items=validated.cases,
                generation_record_id=record.id,
                source="mock" if result.is_mock else "llm",
            )
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_succeeded(
                    db,
                    fresh,
                    {
                        "case_ids": case_ids,
                        "warnings": warnings,
                        "generation_record_id": record.id,
                        "is_mock": result.is_mock,
                    },
                    f"生成 {len(case_ids)} 条测试用例",
                )
                add_log(db, fresh, f"生成 {len(case_ids)} 条测试用例", "info")
            return {"ok": True, "case_ids": case_ids}
        except LLMError as exc:
            db.rollback()
            _record_failure(
                db,
                project_id=project_id,
                task_type="case_generation",
                context=context,
                error=f"{exc.code}: {exc.message} {exc.details or ''}".strip(),
            )
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{exc.code}: {exc.message}", "用例生成失败")
                add_log(db, fresh, f"用例生成失败：{exc.message}", "error")
            return {"ok": False, "error": exc.message}
        except Exception as exc:  # pragma: no cover - defensive worker path
            logger.exception("Case generation failed")
            db.rollback()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{type(exc).__name__}: {exc}", "用例生成失败")
                add_log(db, fresh, "用例生成发生异常，详见执行日志", "error")
            raise
        finally:
            if provider is not None:
                provider.close()

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.enums import TaskStatus, TaskType
from app.models.execution import ExecutionScript, TestExecution, TestResult
from app.models.task import AsyncTask
from app.models.test_script import TestScript
from app.repositories.task_repository import TaskRepository
from app.schemas.execution import (
    ExecutionCancelResponse,
    ExecutionRead,
    TestResultRead,
)
from app.services.task_service import TaskService


class ExecutionService:
    @staticmethod
    def create(
        db: Session,
        *,
        project_id: int,
        user_id: int,
        script_ids: list[int],
        timeout_seconds: int,
        mode: str,
    ) -> tuple[TestExecution, AsyncTask]:
        if mode != "local":
            raise AppError(
                "DOCKER_RUNNER_UNAVAILABLE",
                "当前环境没有可用的 Docker 执行器；本地 MVP 仅启用受限本地模式",
                status_code=409,
            )

        unique_ids = list(dict.fromkeys(script_ids))
        scripts = list(
            db.scalars(
                select(TestScript).where(
                    TestScript.project_id == project_id,
                    TestScript.id.in_(unique_ids),
                    TestScript.deleted_at.is_(None),
                )
            ).all()
        )
        if len(scripts) != len(unique_ids):
            raise NotFoundError("SCRIPT_NOT_FOUND", "部分脚本不存在或不属于当前项目")
        not_validated = [script.id for script in scripts if script.status != "validated"]
        if not_validated:
            raise ConflictError(
                "SCRIPT_NOT_VALIDATED",
                "只有通过安全校验的脚本才能执行",
                details={"script_ids": not_validated},
            )

        task = AsyncTask(
            task_id=str(uuid4()),
            project_id=project_id,
            task_type=TaskType.EXECUTION.value,
            status=TaskStatus.QUEUED.value,
            progress=0,
            message="已排队",
        )
        TaskRepository.create(db, task)
        db.flush()

        execution = TestExecution(
            project_id=project_id,
            task_id=task.task_id,
            status="pending",
            mode=mode,
            timeout_seconds=timeout_seconds,
            created_by=user_id,
        )
        db.add(execution)
        db.flush()
        for script in scripts:
            db.add(
                ExecutionScript(
                    execution_id=execution.id,
                    script_id=script.id,
                    created_at=execution.created_at,
                )
            )
        db.commit()
        db.refresh(execution)
        db.refresh(task)

        from app.tasks.execution_tasks import execute_task

        try:
            execute_task.delay(task.task_id, execution.id)
        except Exception as exc:
            fresh = db.get(TestExecution, execution.id)
            if fresh is not None:
                fresh.status = "error"
                fresh.error_message = f"任务投递失败: {exc}"[:2000]
            task.status = TaskStatus.FAILED.value
            task.error = f"Celery enqueue failed: {exc}"[:4000]
            db.commit()
            raise AppError(
                "TASK_ENQUEUE_FAILED",
                "无法投递执行任务，请确认 Redis 和 worker 已启动",
                status_code=503,
                details=f"{type(exc).__name__}: {exc}"[:300],
            ) from exc

        return execution, task

    @staticmethod
    def get_or_404(db: Session, execution_id: int) -> TestExecution:
        execution = db.get(TestExecution, execution_id)
        if execution is None:
            raise NotFoundError("EXECUTION_NOT_FOUND", "执行记录不存在")
        return execution

    @staticmethod
    def list(
        db: Session,
        project_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[TestExecution], int]:
        conditions = [TestExecution.project_id == project_id]
        if status:
            conditions.append(TestExecution.status == status)
        total = db.scalar(select(func.count(TestExecution.id)).where(*conditions)) or 0
        items = db.scalars(
            select(TestExecution)
            .where(*conditions)
            .order_by(TestExecution.created_at.desc(), TestExecution.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), int(total)

    @staticmethod
    def list_results(db: Session, execution_id: int) -> list[TestResult]:
        return list(
            db.scalars(
                select(TestResult)
                .where(TestResult.execution_id == execution_id)
                .order_by(TestResult.id.asc())
            ).all()
        )

    @staticmethod
    def get_result_or_404(db: Session, result_id: int) -> TestResult:
        result = db.get(TestResult, result_id)
        if result is None:
            raise NotFoundError("RESULT_NOT_FOUND", "测试结果不存在")
        return result

    @staticmethod
    def to_read(execution: TestExecution) -> ExecutionRead:
        return ExecutionRead(
            id=execution.id,
            project_id=execution.project_id,
            task_id=execution.task_id,
            status=execution.status,
            mode=execution.mode,
            timeout_seconds=execution.timeout_seconds,
            total=execution.total,
            passed=execution.passed,
            failed=execution.failed,
            skipped=execution.skipped,
            errors=execution.errors,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
            report_url=(
                f"/api/v1/executions/{execution.id}/report"
                if execution.report_path
                else None
            ),
            log_url=(
                f"/api/v1/executions/{execution.id}/log"
                if execution.log_path
                else None
            ),
            error_message=execution.error_message,
            created_at=execution.created_at,
        )

    @staticmethod
    def to_result_read(result: TestResult) -> TestResultRead:
        return TestResultRead(
            id=result.id,
            execution_id=result.execution_id,
            script_id=result.script_id,
            test_case_id=result.test_case_id,
            node_id=result.node_id,
            test_name=result.test_name,
            status=result.status,
            duration_ms=result.duration_ms,
            failure_message=result.failure_message,
            traceback=result.traceback,
            screenshot_url=(
                f"/api/v1/test-results/{result.id}/screenshot"
                if result.screenshot_path
                else None
            ),
            failure_analysis=result.failure_analysis,
            created_at=result.created_at,
        )

    @staticmethod
    def cancel(db: Session, execution: TestExecution) -> ExecutionCancelResponse:
        if execution.task_id is None:
            raise ConflictError("EXECUTION_CONFLICT", "执行没有关联任务")
        task = TaskRepository.get_by_task_id(db, execution.task_id)
        if task is None:
            raise NotFoundError("TASK_NOT_FOUND", "关联任务不存在")
        task = TaskService.cancel(db, task)
        return ExecutionCancelResponse(
            execution_id=execution.id,
            task_id=execution.task_id,
            status=execution.status,
            cancel_requested=task.cancel_requested,
        )

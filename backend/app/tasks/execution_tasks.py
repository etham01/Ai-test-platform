from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.time import utcnow
from app.execution.local_runner import LocalRunner
from app.models.execution import ExecutionScript, TestExecution, TestResult
from app.models.project import Project
from app.models.test_script import TestScript
from app.tasks.celery_app import celery_app
from app.tasks.task_utils import (
    add_log,
    get_task,
    is_cancel_requested,
    mark_cancelled,
    mark_failed,
    mark_running,
    mark_succeeded,
    task_session,
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="smarttest.execution.run")
def execute_task(self, task_id: str, execution_id: int) -> dict[str, object]:
    with task_session() as db:
        task = get_task(db, task_id)
        execution = db.get(TestExecution, execution_id)
        if task is None or execution is None:
            return {"ok": False}

        try:
            project = db.get(Project, execution.project_id)
            if project is None or project.deleted_at is not None:
                mark_failed(db, task, "项目不存在或已删除", "项目不可用")
                return {"ok": False}

            mark_running(db, task, "准备执行测试脚本", 5)
            execution.status = "running"
            execution.started_at = utcnow()
            execution.celery_task_id = getattr(self.request, "id", None)
            execution.error_message = None
            db.commit()
            add_log(db, task, f"执行 #{execution.id} 开始", "info")

            scripts = list(
                db.scalars(
                    select(TestScript)
                    .join(
                        ExecutionScript,
                        ExecutionScript.script_id == TestScript.id,
                    )
                    .where(ExecutionScript.execution_id == execution.id)
                ).all()
            )
            if not scripts:
                mark_failed(db, task, "没有可执行脚本", "执行失败")
                execution.status = "error"
                execution.error_message = "没有可执行脚本"
                execution.finished_at = utcnow()
                db.commit()
                return {"ok": False}

            runner = LocalRunner()
            artifacts = runner.run(
                execution_id=execution.id,
                scripts=scripts,
                project=project,
                timeout_seconds=execution.timeout_seconds,
                should_cancel=lambda: is_cancel_requested(db, task),
            )

            total = len(artifacts.results)
            passed = sum(1 for item in artifacts.results if item["status"] == "passed")
            failed = sum(1 for item in artifacts.results if item["status"] == "failed")
            errors = sum(1 for item in artifacts.results if item["status"] == "error")
            skipped = sum(1 for item in artifacts.results if item["status"] == "skipped")

            for item in artifacts.results:
                script = item.get("script")
                db.add(
                    TestResult(
                        execution_id=execution.id,
                        project_id=execution.project_id,
                        script_id=script.id if script is not None else None,
                        test_case_id=script.test_case_id if script is not None else None,
                        node_id=item.get("node_id"),
                        test_name=item.get("name") or "unknown",
                        status=item.get("status", "error"),
                        duration_ms=item.get("duration_ms"),
                        failure_message=item.get("failure_message"),
                        traceback=item.get("traceback"),
                        screenshot_path=item.get("screenshot_path"),
                        created_at=utcnow(),
                    )
                )

            execution.status = artifacts.status
            execution.total = total
            execution.passed = passed
            execution.failed = failed
            execution.errors = errors
            execution.skipped = skipped
            execution.finished_at = utcnow()
            execution.report_path = artifacts.report_path
            execution.log_path = artifacts.log_path
            execution.error_message = artifacts.error
            db.commit()

            stats = {
                "execution_id": execution.id,
                "total": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "errors": errors,
                "status": artifacts.status,
            }
            if artifacts.status in {"passed", "failed"}:
                fresh = get_task(db, task_id)
                if fresh is not None:
                    mark_succeeded(
                        db,
                        fresh,
                        stats,
                        f"执行完成：{passed} passed / {failed} failed / {errors} errors",
                    )
                    add_log(
                        db,
                        fresh,
                        f"执行完成：{passed} passed / {failed} failed / {errors} errors",
                        "info" if failed == 0 and errors == 0 else "warning",
                    )
            elif artifacts.status == "cancelled":
                fresh = get_task(db, task_id)
                if fresh is not None:
                    mark_cancelled(db, fresh, "执行已取消")
                    add_log(db, fresh, "执行进程已终止", "warning")
            else:
                fresh = get_task(db, task_id)
                if fresh is not None:
                    mark_failed(
                        db,
                        fresh,
                        artifacts.error or f"执行状态: {artifacts.status}",
                        "执行失败",
                    )
                    add_log(db, fresh, f"执行失败：{artifacts.status}", "error")
            return {"ok": True, **stats}
        except Exception as exc:  # pragma: no cover - defensive worker path
            logger.exception("Execution failed")
            db.rollback()
            execution = db.get(TestExecution, execution_id)
            if execution is not None:
                execution.status = "error"
                execution.error_message = f"{type(exc).__name__}: {exc}"[:4000]
                execution.finished_at = utcnow()
                db.commit()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{type(exc).__name__}: {exc}", "执行失败")
                add_log(db, fresh, "执行发生异常，详见执行日志", "error")
            raise

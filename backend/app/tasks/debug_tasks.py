from __future__ import annotations

import time

from app.tasks.celery_app import celery_app
from app.tasks.task_utils import (
    add_log,
    get_task,
    is_cancel_requested,
    mark_cancelled,
    mark_failed,
    mark_running,
    mark_succeeded,
    set_celery_task_id,
    task_session,
    update_progress,
)


@celery_app.task(bind=True, name="smarttest.debug.ping")
def ping_task(
    self,
    task_id: str,
    message: str = "pong",
    sleep_seconds: float = 0.0,
) -> dict[str, object]:
    """Small task used to verify the Redis/Celery/DB task pipeline."""
    with task_session() as db:
        task = get_task(db, task_id)
        if task is None:
            return {"ok": False, "error": "task not found"}

        try:
            mark_running(db, task, "调试任务开始", 5)
            set_celery_task_id(db, task, getattr(self.request, "id", None))
            add_log(db, task, "调试任务已由 Celery worker 接收", "info")

            deadline = time.monotonic() + max(0.0, float(sleep_seconds))
            while time.monotonic() < deadline:
                if is_cancel_requested(db, task):
                    mark_cancelled(db, task, "调试任务已取消")
                    add_log(db, task, "检测到取消请求，任务终止", "warning")
                    return {"ok": False, "cancelled": True}
                remaining = deadline - time.monotonic()
                time.sleep(min(0.25, max(0.0, remaining)))

            update_progress(db, task, 90, "调试任务即将完成")
            add_log(db, task, f"调试任务完成，message={message}", "info")
            mark_succeeded(db, task, {"message": message, "echo": message})
            return {"ok": True, "message": message}
        except Exception as exc:  # pragma: no cover - defensive worker path
            db.rollback()
            failed = get_task(db, task_id)
            if failed is not None:
                mark_failed(db, failed, f"{type(exc).__name__}: {exc}")
            raise

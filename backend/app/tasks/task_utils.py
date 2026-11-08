from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import redact_text
from app.core.time import utcnow
from app.db.session import SessionLocal
from app.models.enums import TaskStatus
from app.models.task import AsyncTask
from app.repositories.task_repository import TaskRepository


@contextmanager
def task_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_task(db: Session, task_id: str) -> AsyncTask | None:
    return TaskRepository.get_by_task_id(db, task_id)


def adjust_progress(task: AsyncTask, progress: int) -> int:
    return max(0, min(100, int(progress)))


def mark_running(
    db: Session, task: AsyncTask, message: str = "运行中", progress: int = 0
) -> AsyncTask:
    task.status = TaskStatus.RUNNING.value
    task.progress = adjust_progress(task, progress)
    task.message = message[:1024]
    if task.started_at is None:
        task.started_at = utcnow()
    task.error = None
    db.commit()
    db.refresh(task)
    return task


def update_progress(
    db: Session, task: AsyncTask, progress: int, message: str | None = None
) -> AsyncTask:
    task.progress = adjust_progress(task, progress)
    if message is not None:
        task.message = message[:1024]
    db.commit()
    db.refresh(task)
    return task


def add_log(db: Session, task: AsyncTask, message: str, level: str = "info") -> None:
    TaskRepository.add_log(db, task.id, message, level)
    db.commit()


def set_celery_task_id(db: Session, task: AsyncTask, celery_task_id: str | None) -> None:
    if celery_task_id and task.celery_task_id != celery_task_id:
        task.celery_task_id = celery_task_id[:64]
        db.commit()


def mark_succeeded(
    db: Session,
    task: AsyncTask,
    result: dict[str, Any] | None = None,
    message: str = "任务完成",
) -> AsyncTask:
    task.status = TaskStatus.SUCCEEDED.value
    task.progress = 100
    task.message = message[:1024]
    task.result = result
    task.finished_at = utcnow()
    db.commit()
    db.refresh(task)
    return task


def mark_failed(
    db: Session, task: AsyncTask, error: str, message: str = "任务失败"
) -> AsyncTask:
    task.status = TaskStatus.FAILED.value
    task.error = redact_text(error)[:4000]
    task.message = message[:1024]
    task.finished_at = utcnow()
    db.commit()
    db.refresh(task)
    return task


def mark_cancelled(
    db: Session, task: AsyncTask, message: str = "任务已取消"
) -> AsyncTask:
    task.status = TaskStatus.CANCELLED.value
    task.message = message[:1024]
    task.finished_at = utcnow()
    db.commit()
    db.refresh(task)
    return task


def is_cancel_requested(db: Session, task: AsyncTask) -> bool:
    """Read the cancel flag in a fresh transaction.

    The worker's own session may still be inside a REPEATABLE READ snapshot;
    refreshing it repeatedly would never observe the API's committed flag.
    A short-lived independent session guarantees a fresh read.
    """
    with SessionLocal() as check_db:
        value = check_db.scalar(
            select(AsyncTask.cancel_requested).where(AsyncTask.id == task.id)
        )
    return bool(value)

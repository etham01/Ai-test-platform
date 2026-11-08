from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.enums import TaskStatus, TaskType
from app.models.task import AsyncTask, AsyncTaskLog
from app.repositories.task_repository import TaskRepository
from app.tasks.celery_app import celery_app
from app.tasks.debug_tasks import ping_task
from app.tasks.task_utils import mark_failed

logger = logging.getLogger(__name__)


class TaskService:
    @staticmethod
    def get_or_404(db: Session, task_id: str) -> AsyncTask:
        task = TaskRepository.get_by_task_id(db, task_id)
        if task is None:
            raise NotFoundError("TASK_NOT_FOUND", "任务不存在")
        return task

    @staticmethod
    def create_and_dispatch(
        db: Session,
        project_id: int | None,
        task_type: TaskType,
        dispatch: Callable[[str], object],
    ) -> AsyncTask:
        task = AsyncTask(
            task_id=str(uuid4()),
            project_id=project_id,
            task_type=task_type.value,
            status=TaskStatus.QUEUED.value,
            progress=0,
            message="已排队",
        )
        TaskRepository.create(db, task)
        db.commit()
        db.refresh(task)

        try:
            dispatch(task.task_id)
        except Exception as exc:
            logger.exception("Failed to enqueue %s task %s", task_type.value, task.task_id)
            fresh = TaskRepository.get_by_task_id(db, task.task_id)
            if fresh is not None:
                mark_failed(
                    db,
                    fresh,
                    f"Celery enqueue failed: {type(exc).__name__}: {exc}",
                    "任务投递失败",
                )
            raise AppError(
                "TASK_ENQUEUE_FAILED",
                "无法投递 Celery 任务，请确认 Redis 和 worker 已启动",
                status_code=503,
                details=f"{type(exc).__name__}: {exc}"[:300],
            ) from exc

        db.refresh(task)
        return task

    @staticmethod
    def create_debug(
        db: Session,
        project_id: int | None,
        message: str,
        sleep_seconds: float,
    ) -> AsyncTask:
        return TaskService.create_and_dispatch(
            db,
            project_id,
            TaskType.DEBUG,
            lambda task_id: ping_task.delay(task_id, message, sleep_seconds),
        )

    @staticmethod
    def list_logs(
        db: Session, task_id: str, limit: int = 200
    ) -> tuple[list[AsyncTaskLog], int]:
        task = TaskService.get_or_404(db, task_id)
        return TaskRepository.list_logs(db, task.id, limit=limit)

    @staticmethod
    def cancel(db: Session, task: AsyncTask) -> AsyncTask:
        task.cancel_requested = True
        db.commit()
        db.refresh(task)

        if task.celery_task_id:
            try:
                # terminate=False: the task itself checks the DB flag between steps.
                celery_app.control.revoke(task.celery_task_id, terminate=False)
            except Exception:  # pragma: no cover - broker may be unavailable
                logger.warning("Celery revoke failed for task %s", task.task_id)
        return task

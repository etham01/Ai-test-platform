from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.task import AsyncTask, AsyncTaskLog


class TaskRepository:
    @staticmethod
    def create(db: Session, task: AsyncTask) -> AsyncTask:
        db.add(task)
        db.flush()
        return task

    @staticmethod
    def get_by_task_id(db: Session, task_id: str) -> AsyncTask | None:
        return db.scalar(select(AsyncTask).where(AsyncTask.task_id == task_id))

    @staticmethod
    def add_log(
        db: Session,
        task_ref_id: int,
        message: str,
        level: str = "info",
    ) -> AsyncTaskLog:
        log = AsyncTaskLog(
            async_task_ref_id=task_ref_id,
            level=level,
            message=message[:2048],
        )
        db.add(log)
        db.flush()
        return log

    @staticmethod
    def list_logs(
        db: Session, task_ref_id: int, limit: int = 200
    ) -> tuple[list[AsyncTaskLog], int]:
        total = (
            db.scalar(
                select(func.count(AsyncTaskLog.id)).where(
                    AsyncTaskLog.async_task_ref_id == task_ref_id
                )
            )
            or 0
        )
        items = db.scalars(
            select(AsyncTaskLog)
            .where(AsyncTaskLog.async_task_ref_id == task_ref_id)
            .order_by(AsyncTaskLog.created_at.asc(), AsyncTaskLog.id.asc())
            .limit(limit)
        ).all()
        return list(items), int(total)

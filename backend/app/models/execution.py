from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import UTCDateTime
from app.db.base import Base, TimestampMixin


class TestExecution(Base, TimestampMixin):
    __tablename__ = "test_executions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    mode: Mapped[str] = mapped_column(String(16), default="local", nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    report_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    log_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class ExecutionScript(Base):
    __tablename__ = "execution_scripts"
    __table_args__ = (
        UniqueConstraint("execution_id", "script_id", name="uq_execution_scripts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("test_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    script_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("test_scripts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("test_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    script_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("test_scripts.id", ondelete="SET NULL"),
        nullable=True,
    )
    test_case_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("test_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    node_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    test_name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    failure_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    analysis_generation_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("generation_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

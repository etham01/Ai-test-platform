from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class TestCase(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("project_id", "case_code", name="uq_test_cases_project_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    requirement_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("test_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    case_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    module: Mapped[str | None] = mapped_column(String(128), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="P2", nullable=False)
    preconditions: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    related_page_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    test_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    expected_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    assertions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    assumptions: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    generation_source: Mapped[str] = mapped_column(
        String(32), default="user", nullable=False
    )
    generation_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("generation_records.id", ondelete="SET NULL"),
        nullable=True,
    )

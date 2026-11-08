from __future__ import annotations

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

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class TestScript(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "test_scripts"
    __table_args__ = (
        UniqueConstraint(
            "test_case_id", "version", name="uq_test_scripts_case_version"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("test_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    validation_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    generation_source: Mapped[str] = mapped_column(
        String(32), default="user", nullable=False
    )
    generation_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("generation_records.id", ondelete="SET NULL"),
        nullable=True,
    )

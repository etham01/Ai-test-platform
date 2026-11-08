from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class Workflow(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "workflows"

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
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    involved_page_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="inferred", nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    generation_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("generation_records.id", ondelete="SET NULL"),
        nullable=True,
    )

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import UTCDateTime
from app.db.base import Base, TimestampMixin


class WebPage(Base, TimestampMixin):
    __tablename__ = "web_pages"
    __table_args__ = (
        UniqueConstraint("project_id", "url_hash", name="uq_web_pages_project_url"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="discovered", nullable=False, index=True
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    text_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    dom_snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    discovered_from_page_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("web_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(32), default="link", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class PageElement(Base):
    __tablename__ = "page_elements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("web_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    element_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accessible_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    label: Mapped[str | None] = mapped_column(String(512), nullable=True)
    placeholder: Mapped[str | None] = mapped_column(String(512), nullable=True)
    text: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    element_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    input_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    href: Mapped[str | None] = mapped_column(Text, nullable=True)
    selector_candidates: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class PageRelation(Base):
    __tablename__ = "page_relations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    from_page_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("web_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_page_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("web_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

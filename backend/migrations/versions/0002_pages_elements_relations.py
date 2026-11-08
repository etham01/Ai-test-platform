"""pages, elements and relations

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UTC_DATETIME = mysql.DATETIME(fsp=6)


def upgrade() -> None:
    op.create_table(
        "web_pages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("depth", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'discovered'"),
            nullable=False,
        ),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("text_summary", sa.Text(), nullable=True),
        sa.Column("dom_snapshot_path", sa.String(length=512), nullable=True),
        sa.Column("screenshot_path", sa.String(length=512), nullable=True),
        sa.Column("discovered_from_page_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "source",
            sa.String(length=32),
            server_default=sa.text("'link'"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("fetched_at", UTC_DATETIME, nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_web_pages_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["discovered_from_page_id"],
            ["web_pages.id"],
            name="fk_web_pages_discovered_from_page_id_web_pages",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_web_pages"),
        sa.UniqueConstraint("project_id", "url_hash", name="uq_web_pages_project_url"),
    )
    op.create_index("ix_web_pages_project_id", "web_pages", ["project_id"], unique=False)
    op.create_index("ix_web_pages_url_hash", "web_pages", ["url_hash"], unique=False)
    op.create_index("ix_web_pages_status", "web_pages", ["status"], unique=False)
    op.create_index(
        "ix_web_pages_discovered_from_page_id",
        "web_pages",
        ["discovered_from_page_id"],
        unique=False,
    )

    op.create_table(
        "page_elements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("page_id", sa.BigInteger(), nullable=False),
        sa.Column("element_type", sa.String(length=32), nullable=False),
        sa.Column("tag", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=True),
        sa.Column("accessible_name", sa.String(length=512), nullable=True),
        sa.Column("label", sa.String(length=512), nullable=True),
        sa.Column("placeholder", sa.String(length=512), nullable=True),
        sa.Column("text", sa.String(length=1024), nullable=True),
        sa.Column("element_id", sa.String(length=256), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("input_type", sa.String(length=64), nullable=True),
        sa.Column("href", sa.Text(), nullable=True),
        sa.Column("selector_candidates", sa.JSON(), nullable=True),
        sa.Column(
            "is_sensitive",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_page_elements_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["page_id"],
            ["web_pages.id"],
            name="fk_page_elements_page_id_web_pages",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_page_elements"),
    )
    op.create_index(
        "ix_page_elements_project_id", "page_elements", ["project_id"], unique=False
    )
    op.create_index("ix_page_elements_page_id", "page_elements", ["page_id"], unique=False)
    op.create_index(
        "ix_page_elements_element_type", "page_elements", ["element_type"], unique=False
    )

    op.create_table(
        "page_relations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("from_page_id", sa.BigInteger(), nullable=False),
        sa.Column("to_page_id", sa.BigInteger(), nullable=True),
        sa.Column("target_url", sa.String(length=2048), nullable=True),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "confidence", sa.Float(), server_default=sa.text("1.0"), nullable=False
        ),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_page_relations_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["from_page_id"],
            ["web_pages.id"],
            name="fk_page_relations_from_page_id_web_pages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_page_id"],
            ["web_pages.id"],
            name="fk_page_relations_to_page_id_web_pages",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_page_relations"),
    )
    op.create_index(
        "ix_page_relations_project_id", "page_relations", ["project_id"], unique=False
    )
    op.create_index(
        "ix_page_relations_from_page_id",
        "page_relations",
        ["from_page_id"],
        unique=False,
    )
    op.create_index(
        "ix_page_relations_to_page_id", "page_relations", ["to_page_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("page_relations")
    op.drop_table("page_elements")
    op.drop_table("web_pages")

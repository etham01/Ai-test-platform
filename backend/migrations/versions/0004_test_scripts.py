"""test scripts

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UTC_DATETIME = mysql.DATETIME(fsp=6)


def upgrade() -> None:
    op.create_table(
        "test_scripts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("test_case_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("validation_report", sa.JSON(), nullable=True),
        sa.Column(
            "generation_source",
            sa.String(length=32),
            server_default=sa.text("'user'"),
            nullable=False,
        ),
        sa.Column("generation_record_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.Column("deleted_at", UTC_DATETIME, nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_test_scripts_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_cases.id"],
            name="fk_test_scripts_test_case_id_test_cases",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["generation_record_id"],
            ["generation_records.id"],
            name="fk_test_scripts_generation_record_id_generation_records",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_scripts"),
        sa.UniqueConstraint(
            "test_case_id", "version", name="uq_test_scripts_case_version"
        ),
    )
    op.create_index(
        "ix_test_scripts_project_id", "test_scripts", ["project_id"], unique=False
    )
    op.create_index(
        "ix_test_scripts_test_case_id", "test_scripts", ["test_case_id"], unique=False
    )
    op.create_index(
        "ix_test_scripts_deleted_at", "test_scripts", ["deleted_at"], unique=False
    )


def downgrade() -> None:
    op.drop_table("test_scripts")

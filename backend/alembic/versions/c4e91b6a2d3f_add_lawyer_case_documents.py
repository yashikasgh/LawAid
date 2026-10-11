"""add lawyer case document persistence

Revision ID: c4e91b6a2d3f
Revises: b7f41c4a98d1
Create Date: 2026-10-10 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e91b6a2d3f"
down_revision: Union[str, Sequence[str], None] = "b7f41c4a98d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lawyer_cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lawyer_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["lawyer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lawyer_cases_lawyer_id"), "lawyer_cases", ["lawyer_id"], unique=False)
    op.create_table(
        "case_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_ref", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extracted_entities", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("ocr_used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["lawyer_cases.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_ref"),
    )
    op.create_index(op.f("ix_case_documents_case_id"), "case_documents", ["case_id"], unique=False)
    op.create_index(op.f("ix_case_documents_uploaded_by"), "case_documents", ["uploaded_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_case_documents_uploaded_by"), table_name="case_documents")
    op.drop_index(op.f("ix_case_documents_case_id"), table_name="case_documents")
    op.drop_table("case_documents")
    op.drop_index(op.f("ix_lawyer_cases_lawyer_id"), table_name="lawyer_cases")
    op.drop_table("lawyer_cases")

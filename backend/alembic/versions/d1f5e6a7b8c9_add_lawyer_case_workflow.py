"""add lawyer analysis timeline and summary persistence

Revision ID: d1f5e6a7b8c9
Revises: c4e91b6a2d3f
Create Date: 2026-10-10 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "d1f5e6a7b8c9"
down_revision = "c4e91b6a2d3f"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("case_analyses", sa.Column("id", sa.String(36), primary_key=True), sa.Column("case_id", sa.String(36), sa.ForeignKey("lawyer_cases.id"), nullable=False, unique=True), sa.Column("payload", sa.Text(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("error_message", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True)))
    op.create_index("ix_case_analyses_case_id", "case_analyses", ["case_id"])
    op.create_table("case_timeline_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("case_id", sa.String(36), sa.ForeignKey("lawyer_cases.id"), nullable=False), sa.Column("source_document_id", sa.String(36), sa.ForeignKey("case_documents.id")), sa.Column("event_date", sa.String(10), nullable=False), sa.Column("event_time", sa.String(20)), sa.Column("title", sa.String(300), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("event_type", sa.String(40), nullable=False), sa.Column("related_bns_sections", sa.Text(), nullable=False), sa.Column("source_reference", sa.Text()), sa.Column("confidence", sa.String(20), nullable=False), sa.Column("is_edited", sa.String(5), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True)))
    op.create_index("ix_case_timeline_events_case_id", "case_timeline_events", ["case_id"])
    op.create_table("case_summaries", sa.Column("id", sa.String(36), primary_key=True), sa.Column("case_id", sa.String(36), sa.ForeignKey("lawyer_cases.id"), nullable=False, unique=True), sa.Column("executive_summary", sa.Text(), nullable=False), sa.Column("current_stage", sa.String(120)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True)))
    op.create_index("ix_case_summaries_case_id", "case_summaries", ["case_id"])

def downgrade():
    op.drop_index("ix_case_summaries_case_id", table_name="case_summaries"); op.drop_table("case_summaries")
    op.drop_index("ix_case_timeline_events_case_id", table_name="case_timeline_events"); op.drop_table("case_timeline_events")
    op.drop_index("ix_case_analyses_case_id", table_name="case_analyses"); op.drop_table("case_analyses")

"""add page-level case document extraction details

Revision ID: e2a6f7b8c9d0
Revises: d1f5e6a7b8c9
"""
from alembic import op
import sqlalchemy as sa

revision = "e2a6f7b8c9d0"
down_revision = "d1f5e6a7b8c9"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("case_documents", sa.Column("extraction_details", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("case_documents", "extraction_details")

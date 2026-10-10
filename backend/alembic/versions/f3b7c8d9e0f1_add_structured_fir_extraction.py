"""persist structured FIR extraction

Revision ID: f3b7c8d9e0f1
Revises: e2a6f7b8c9d0
"""
from alembic import op
import sqlalchemy as sa
revision = "f3b7c8d9e0f1"
down_revision = "e2a6f7b8c9d0"
branch_labels = None
depends_on = None
def upgrade(): op.add_column("case_documents", sa.Column("structured_extraction", sa.Text(), nullable=True))
def downgrade(): op.drop_column("case_documents", "structured_extraction")

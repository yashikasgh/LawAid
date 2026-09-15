"""add complaints and password resets

Revision ID: f3d5f8a0a1b2
Revises: e130ed9b43c2
Create Date: 2026-09-16 00:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f3d5f8a0a1b2"
down_revision: Union[str, Sequence[str], None] = "e130ed9b43c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("complaint_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("detected_sections", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("duplicate_status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_complaints_id"), "complaints", ["id"], unique=False)
    
    op.create_table(
        "password_resets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_password_resets_id"), "password_resets", ["id"], unique=False)
    op.create_index(op.f("ix_password_resets_token_hash"), "password_resets", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_password_resets_token_hash"), table_name="password_resets")
    op.drop_index(op.f("ix_password_resets_id"), table_name="password_resets")
    op.drop_table("password_resets")
    
    op.drop_index(op.f("ix_complaints_id"), table_name="complaints")
    op.drop_table("complaints")


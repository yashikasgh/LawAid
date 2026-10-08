"""add FIR digital approval signature metadata

Revision ID: b7f41c4a98d1
Revises: e130ed9b43c2
Create Date: 2026-10-08 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7f41c4a98d1"
down_revision: Union[str, Sequence[str], None] = "f3d5f8a0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fir_registry",
        sa.Column("signature_status", sa.String(), nullable=False, server_default="NOT_VERIFIED"),
    )
    op.add_column("fir_registry", sa.Column("signed_by", sa.String(), nullable=True))
    op.add_column("fir_registry", sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("fir_registry", "signature_status", server_default=None)


def downgrade() -> None:
    op.drop_column("fir_registry", "signed_at")
    op.drop_column("fir_registry", "signed_by")
    op.drop_column("fir_registry", "signature_status")

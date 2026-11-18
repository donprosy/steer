"""Add business profile details.

Revision ID: c51d47a9291f
Revises: a4d23d7d11a5
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


revision = "c51d47a9291f"
down_revision = "a4d23d7d11a5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("businesses", sa.Column("industry", sa.String(length=80), nullable=True))
    op.add_column("businesses", sa.Column("contact_email", sa.String(length=254), nullable=True))
    op.add_column("businesses", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("businesses", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column(
        "businesses",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="NGN"),
    )


def downgrade():
    op.drop_column("businesses", "currency")
    op.drop_column("businesses", "address")
    op.drop_column("businesses", "phone")
    op.drop_column("businesses", "contact_email")
    op.drop_column("businesses", "industry")

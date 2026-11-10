"""Add business-scoped customers.

Revision ID: be3c2a61d941
Revises: 3d93b1674a22
Create Date: 2026-11-09

"""
from alembic import op
import sqlalchemy as sa


revision = "be3c2a61d941"
down_revision = "3d93b1674a22"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(full_name)) > 0", name="ck_customer_full_name"
        ),
        sa.CheckConstraint("length(trim(phone)) > 0", name="ck_customer_phone"),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customers_business_created", "customers", ["business_id", "created_at"]
    )
    op.create_index(
        "ix_customers_business_name", "customers", ["business_id", "full_name"]
    )
    op.create_index(
        "ix_customers_business_phone", "customers", ["business_id", "phone"]
    )
    op.create_index(
        "ix_customers_business_email", "customers", ["business_id", "email"]
    )


def downgrade():
    op.drop_index("ix_customers_business_email", table_name="customers")
    op.drop_index("ix_customers_business_phone", table_name="customers")
    op.drop_index("ix_customers_business_name", table_name="customers")
    op.drop_index("ix_customers_business_created", table_name="customers")
    op.drop_table("customers")

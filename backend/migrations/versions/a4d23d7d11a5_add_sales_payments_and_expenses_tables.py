"""Add sales, sale items, payments and operating expense tables.

Revision ID: a4d23d7d11a5
Revises: 9b2f7d137b2f
Create Date: 2026-11-09

"""

from alembic import op
import sqlalchemy as sa


revision = "a4d23d7d11a5"
down_revision = "9b2f7d137b2f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sales",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=True),
        sa.Column("reference_number", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sale_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'partially_paid', 'paid', 'cancelled', 'refunded')", name="ck_sale_status"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "reference_number", name="uq_sale_business_reference"),
    )
    op.create_index("ix_sales_business_created", "sales", ["business_id", "created_at"])
    op.create_index("ix_sales_business_customer", "sales", ["business_id", "customer_id"])

    op.create_table(
        "sale_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sale_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_items_sale_created", "sale_items", ["sale_id", "created_at"])

    op.create_table(
        "payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("sale_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=True),
        sa.Column("method", sa.String(length=24), nullable=False, server_default="cash"),
        sa.Column("direction", sa.String(length=16), nullable=False, server_default="incoming"),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="received"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("method IN ('cash', 'bank_transfer', 'pos', 'other')", name="ck_payment_method"),
        sa.CheckConstraint("direction IN ('incoming', 'refund')", name="ck_payment_direction"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference", name="uq_payment_reference"),
    )
    op.create_index("ix_payments_sale_created", "payments", ["sale_id", "created_at"])
    op.create_index("ix_payments_business_date", "payments", ["business_id", "payment_date"])

    op.create_table(
        "expenses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.String(length=24), nullable=False, server_default="cash"),
        sa.Column("expense_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("payment_method IN ('cash', 'bank_transfer', 'pos', 'other')", name="ck_expense_payment_method"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expenses_business_date", "expenses", ["business_id", "expense_date"])
    op.create_index("ix_expenses_business_category", "expenses", ["business_id", "category"])


def downgrade():
    op.drop_index("ix_expenses_business_category", table_name="expenses")
    op.drop_index("ix_expenses_business_date", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_payments_business_date", table_name="payments")
    op.drop_index("ix_payments_sale_created", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_sale_items_sale_created", table_name="sale_items")
    op.drop_table("sale_items")
    op.drop_index("ix_sales_business_customer", table_name="sales")
    op.drop_index("ix_sales_business_created", table_name="sales")
    op.drop_table("sales")

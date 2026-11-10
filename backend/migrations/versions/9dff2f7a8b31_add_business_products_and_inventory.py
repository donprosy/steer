"""Add business products and inventory movement history.

Revision ID: 9dff2f7a8b31
Revises: be3c2a61d941
Create Date: 2026-11-09

"""

from alembic import op
import sqlalchemy as sa


revision = "9dff2f7a8b31"
down_revision = "be3c2a61d941"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False, server_default="product"),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("selling_price", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("purchase_cost", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("quantity_on_hand", sa.Numeric(precision=18, scale=3), nullable=False, server_default="0"),
        sa.Column("reorder_level", sa.Numeric(precision=18, scale=3), nullable=False, server_default="0"),
        sa.Column("stock_unit", sa.String(length=32), nullable=False, server_default="unit"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("type IN ('product', 'service')", name="ck_product_type"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_product_name"),
        sa.CheckConstraint("selling_price >= 0", name="ck_product_selling_price"),
        sa.CheckConstraint("purchase_cost >= 0", name="ck_product_purchase_cost"),
        sa.CheckConstraint("quantity_on_hand >= 0", name="ck_product_quantity_on_hand"),
        sa.CheckConstraint("reorder_level >= 0", name="ck_product_reorder_level"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_products_business_created", "products", ["business_id", "created_at"]
    )
    op.create_index(
        "ix_products_business_category", "products", ["business_id", "category"]
    )
    op.create_index(
        "ix_products_business_type", "products", ["business_id", "type"]
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("delta_quantity", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("quantity_after", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity_after >= 0", name="ck_inventory_movement_quantity_after"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_movements_business_product",
        "inventory_movements",
        ["business_id", "product_id"],
    )
    op.create_index(
        "ix_inventory_movements_product_created",
        "inventory_movements",
        ["product_id", "created_at"],
    )


def downgrade():
    op.drop_index("ix_inventory_movements_product_created", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_business_product", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_index("ix_products_business_type", table_name="products")
    op.drop_index("ix_products_business_category", table_name="products")
    op.drop_index("ix_products_business_created", table_name="products")
    op.drop_table("products")

"""Business product and service catalog."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.CheckConstraint("type IN ('product', 'service')", name="ck_product_type"),
        db.CheckConstraint("length(trim(name)) > 0", name="ck_product_name"),
        db.CheckConstraint("selling_price >= 0", name="ck_product_selling_price"),
        db.CheckConstraint("purchase_cost >= 0", name="ck_product_purchase_cost"),
        db.CheckConstraint("quantity_on_hand >= 0", name="ck_product_quantity_on_hand"),
        db.CheckConstraint("reorder_level >= 0", name="ck_product_reorder_level"),
        db.Index("ix_products_business_created", "business_id", "created_at"),
        db.Index("ix_products_business_category", "business_id", "category"),
        db.Index("ix_products_business_type", "business_id", "type"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="General")
    type = db.Column(db.String(16), nullable=False, default="product")
    sku = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=True)
    selling_price = db.Column(db.Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    purchase_cost = db.Column(db.Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    quantity_on_hand = db.Column(db.Numeric(18, 3), nullable=False, default=Decimal("0"))
    reorder_level = db.Column(db.Numeric(18, 3), nullable=False, default=Decimal("0"))
    stock_unit = db.Column(db.String(32), nullable=False, default="unit")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    business = db.relationship("Business", back_populates="products")
    inventory_movements = db.relationship(
        "InventoryMovement",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="InventoryMovement.created_at.desc()",
    )
    sale_items = db.relationship("SaleItem", back_populates="product")

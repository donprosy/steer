"""Inventory movement history for products."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class InventoryMovement(db.Model):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        db.CheckConstraint("quantity_after >= 0", name="ck_inventory_movement_quantity_after"),
        db.Index("ix_inventory_movements_business_product", "business_id", "product_id"),
        db.Index("ix_inventory_movements_product_created", "product_id", "created_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id = db.Column(
        db.String(36),
        db.ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    delta_quantity = db.Column(db.Numeric(18, 3), nullable=False)
    quantity_after = db.Column(db.Numeric(18, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(18, 2), nullable=True)
    reason = db.Column(db.String(64), nullable=False, default="adjustment")
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    business = db.relationship("Business", back_populates="inventory_movements")
    product = db.relationship("Product", back_populates="inventory_movements")
    user = db.relationship("User", backref="inventory_movements")

"""Line items for sales."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class SaleItem(db.Model):
    __tablename__ = "sale_items"
    __table_args__ = (
        db.Index("ix_sale_items_sale_created", "sale_id", "created_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sale_id = db.Column(db.String(36), db.ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Numeric(18, 3), nullable=False, default=0)
    unit_price = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    unit_cost = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    sale = db.relationship("Sale", back_populates="items")
    product = db.relationship("Product", back_populates="sale_items")

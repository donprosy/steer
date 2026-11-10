"""Business sale records."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class Sale(db.Model):
    __tablename__ = "sales"
    __table_args__ = (
        db.CheckConstraint("status IN ('pending', 'partially_paid', 'paid', 'cancelled', 'refunded')", name="ck_sale_status"),
        db.Index("ix_sales_business_created", "business_id", "created_at"),
        db.Index("ix_sales_business_customer", "business_id", "customer_id"),
        db.UniqueConstraint("business_id", "reference_number", name="uq_sale_business_reference"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(db.String(36), db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    reference_number = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="pending")
    total_amount = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    sale_date = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    business = db.relationship("Business", back_populates="sales")
    customer = db.relationship("Customer", back_populates="sales")
    items = db.relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="sale", cascade="all, delete-orphan")

"""Business-owned customer records."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class Customer(db.Model):
    __tablename__ = "customers"
    __table_args__ = (
        db.CheckConstraint("length(trim(full_name)) > 0", name="ck_customer_full_name"),
        db.CheckConstraint("length(trim(phone)) > 0", name="ck_customer_phone"),
        db.Index("ix_customers_business_created", "business_id", "created_at"),
        db.Index("ix_customers_business_name", "business_id", "full_name"),
        db.Index("ix_customers_business_phone", "business_id", "phone"),
        db.Index("ix_customers_business_email", "business_id", "email"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    full_name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(254), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    business = db.relationship("Business", back_populates="customers")
    sales = db.relationship("Sale", back_populates="customer")
    payments = db.relationship("Payment", back_populates="customer")

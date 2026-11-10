"""Sale payment and refund records."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class Payment(db.Model):
    __tablename__ = "payments"
    __table_args__ = (
        db.CheckConstraint("method IN ('cash', 'bank_transfer', 'pos', 'other')", name="ck_payment_method"),
        db.CheckConstraint("direction IN ('incoming', 'refund')", name="ck_payment_direction"),
        db.Index("ix_payments_sale_created", "sale_id", "created_at"),
        db.Index("ix_payments_business_date", "business_id", "payment_date"),
        db.UniqueConstraint("reference", name="uq_payment_reference"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(db.String(36), db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    sale_id = db.Column(db.String(36), db.ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    method = db.Column(db.String(24), nullable=False, default="cash")
    direction = db.Column(db.String(16), nullable=False, default="incoming")
    amount = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    payment_date = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    reference = db.Column(db.String(64), nullable=False, unique=True)
    status = db.Column(db.String(16), nullable=False, default="received")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    business = db.relationship("Business", back_populates="payments")
    sale = db.relationship("Sale", back_populates="payments")
    customer = db.relationship("Customer", back_populates="payments")

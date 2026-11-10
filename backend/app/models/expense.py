"""Business operating expenses."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class Expense(db.Model):
    __tablename__ = "expenses"
    __table_args__ = (
        db.CheckConstraint("payment_method IN ('cash', 'bank_transfer', 'pos', 'other')", name="ck_expense_payment_method"),
        db.Index("ix_expenses_business_date", "business_id", "expense_date"),
        db.Index("ix_expenses_business_category", "business_id", "category"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(db.String(36), db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    payment_method = db.Column(db.String(24), nullable=False, default="cash")
    expense_date = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    business = db.relationship("Business", back_populates="expenses")

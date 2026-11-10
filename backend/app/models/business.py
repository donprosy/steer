"""Minimal business workspace required for owner membership."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class Business(db.Model):
    __tablename__ = "businesses"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(160), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="active")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    memberships = db.relationship(
        "BusinessMembership", back_populates="business", cascade="all, delete-orphan"
    )
    customers = db.relationship(
        "Customer", back_populates="business", cascade="all, delete-orphan"
    )
    products = db.relationship(
        "Product", back_populates="business", cascade="all, delete-orphan"
    )
    inventory_movements = db.relationship(
        "InventoryMovement",
        back_populates="business",
        cascade="all, delete-orphan",
    )
    sales = db.relationship("Sale", back_populates="business", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="business", cascade="all, delete-orphan")
    expenses = db.relationship("Expense", back_populates="business", cascade="all, delete-orphan")

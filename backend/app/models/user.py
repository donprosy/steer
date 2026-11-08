"""User identity model."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint(
            "system_role IN ('business_owner', 'admin')",
            name="ck_user_system_role",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    system_role = db.Column(
        db.String(24), nullable=False, default="business_owner", server_default="business_owner"
    )
    email_verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    memberships = db.relationship(
        "BusinessMembership", back_populates="user", cascade="all, delete-orphan"
    )
    auth_sessions = db.relationship(
        "AuthSession", back_populates="user", cascade="all, delete-orphan"
    )
    auth_tokens = db.relationship(
        "AuthToken", back_populates="user", cascade="all, delete-orphan"
    )

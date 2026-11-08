"""Hashed one-time email verification and password reset tokens."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class AuthToken(db.Model):
    __tablename__ = "auth_tokens"
    __table_args__ = (
        db.CheckConstraint(
            "purpose IN ('email_verification', 'password_reset')",
            name="ck_auth_token_purpose",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose = db.Column(db.String(32), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)

    user = db.relationship("User", back_populates="auth_tokens")

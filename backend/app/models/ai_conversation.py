"""Tenant-owned AI conversation records."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class AiConversation(db.Model):
    __tablename__ = "ai_conversations"
    __table_args__ = (
        db.Index("ix_ai_conversations_business_updated", "business_id", "updated_at"),
        db.Index("ix_ai_conversations_user_updated", "user_id", "updated_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(db.String(36), db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(160), nullable=False, default="New business conversation")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    messages = db.relationship(
        "AiMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AiMessage.created_at.asc()",
    )

"""Messages inside tenant-owned AI conversations."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class AiMessage(db.Model):
    __tablename__ = "ai_messages"
    __table_args__ = (
        db.CheckConstraint("role IN ('user', 'assistant')", name="ck_ai_message_role"),
        db.Index("ix_ai_messages_conversation_created", "conversation_id", "created_at"),
        db.UniqueConstraint("conversation_id", "request_id", name="uq_ai_message_request"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(16), nullable=False)
    content = db.Column(db.Text, nullable=False)
    request_id = db.Column(db.String(64), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    conversation = db.relationship("AiConversation", back_populates="messages")

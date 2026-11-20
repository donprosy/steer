"""Successful AI reply usage for future subscription limits."""

import uuid
from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc)


class AiUsageRecord(db.Model):
    __tablename__ = "ai_usage_records"
    __table_args__ = (
        db.Index("ix_ai_usage_business_period", "business_id", "period_start", "period_end"),
        db.UniqueConstraint("business_id", "request_id", name="uq_ai_usage_request"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(db.String(36), db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    conversation_id = db.Column(db.String(36), nullable=True)
    request_id = db.Column(db.String(64), nullable=False)
    plan_key = db.Column(db.String(24), nullable=False, default="starter")
    period_start = db.Column(db.DateTime(timezone=True), nullable=False)
    period_end = db.Column(db.DateTime(timezone=True), nullable=False)
    provider = db.Column(db.String(64), nullable=False, default="not-configured")
    model = db.Column(db.String(128), nullable=True)
    input_tokens = db.Column(db.Integer, nullable=True)
    output_tokens = db.Column(db.Integer, nullable=True)
    estimated_cost = db.Column(db.Numeric(18, 6), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

"""User access to a business workspace."""

import uuid

from app import db


class BusinessMembership(db.Model):
    __tablename__ = "business_memberships"
    __table_args__ = (
        db.UniqueConstraint("business_id", "user_id", name="uq_membership_business_user"),
        db.CheckConstraint(
            "role IN ('owner', 'manager', 'staff')", name="ck_membership_role"
        ),
        db.CheckConstraint(
            "status IN ('active', 'suspended')", name="ck_membership_status"
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = db.Column(
        db.String(36), db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = db.Column(db.String(16), nullable=False, default="owner")
    status = db.Column(db.String(16), nullable=False, default="active")

    business = db.relationship("Business", back_populates="memberships")
    user = db.relationship("User", back_populates="memberships")

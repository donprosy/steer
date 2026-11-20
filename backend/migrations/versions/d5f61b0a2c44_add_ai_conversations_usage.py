"""add ai conversations usage

Revision ID: d5f61b0a2c44
Revises: c51d47a9291f
Create Date: 2026-11-18
"""

from alembic import op
import sqlalchemy as sa


revision = "d5f61b0a2c44"
down_revision = "c51d47a9291f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_conversations_business_updated", "ai_conversations", ["business_id", "updated_at"])
    op.create_index("ix_ai_conversations_user_updated", "ai_conversations", ["user_id", "updated_at"])

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_ai_message_role"),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "request_id", name="uq_ai_message_request"),
    )
    op.create_index("ix_ai_messages_conversation_created", "ai_messages", ["conversation_id", "created_at"])

    op.create_table(
        "ai_usage_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("plan_key", sa.String(length=24), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "request_id", name="uq_ai_usage_request"),
    )
    op.create_index("ix_ai_usage_business_period", "ai_usage_records", ["business_id", "period_start", "period_end"])


def downgrade():
    op.drop_index("ix_ai_usage_business_period", table_name="ai_usage_records")
    op.drop_table("ai_usage_records")
    op.drop_index("ix_ai_messages_conversation_created", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_conversations_user_updated", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_business_updated", table_name="ai_conversations")
    op.drop_table("ai_conversations")

"""Add the platform system role field to users.

Revision ID: 9b2f7d137b2f
Revises: 9dff2f7a8b31
Create Date: 2026-11-09

"""

from alembic import op
import sqlalchemy as sa


revision = "9b2f7d137b2f"
down_revision = "9dff2f7a8b31"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "system_role",
                sa.String(length=24),
                nullable=False,
                server_default="business_owner",
            )
        )
        batch_op.create_check_constraint(
            "ck_user_system_role",
            "system_role IN ('business_owner', 'admin')",
        )
        batch_op.alter_column("system_role", server_default=None)


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("ck_user_system_role", type_="check")
        batch_op.drop_column("system_role")

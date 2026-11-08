"""Add login OTP challenges.

Revision ID: 3d93b1674a22
Revises: c883d3d683ce
Create Date: 2026-11-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3d93b1674a22"
down_revision = "c883d3d683ce"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("auth_tokens", schema=None) as batch_op:
        batch_op.drop_constraint("ck_auth_token_purpose", type_="check")
        batch_op.create_check_constraint(
            "ck_auth_token_purpose",
            "purpose IN ('email_verification', 'password_reset', 'login_otp')",
        )
        batch_op.add_column(
            sa.Column("remember_me", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.alter_column("remember_me", server_default=None)


def downgrade():
    op.execute("DELETE FROM auth_tokens WHERE purpose = 'login_otp'")
    with op.batch_alter_table("auth_tokens", schema=None) as batch_op:
        batch_op.drop_constraint("ck_auth_token_purpose", type_="check")
        batch_op.create_check_constraint(
            "ck_auth_token_purpose",
            "purpose IN ('email_verification', 'password_reset')",
        )
        batch_op.drop_column("remember_me")

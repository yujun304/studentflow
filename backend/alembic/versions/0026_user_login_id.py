"""add user login id

Revision ID: 0026_user_login_id
Revises: 0025_dynamic_onboarding
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_user_login_id"
down_revision: str | None = "0025_dynamic_onboarding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("login_id", sa.String(length=100)))
    op.create_index("ix_users_login_id", "users", ["login_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_login_id", table_name="users")
    op.drop_column("users", "login_id")

"""correct roster name and promote the test account

Revision ID: 0027_account_corrections
Revises: 0026_user_login_id
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0027_account_corrections"
down_revision: str | None = "0026_user_login_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE users "
        "SET name = '최현규', login_id = '최현규', updated_at = NOW() "
        "WHERE email = '20628@studentflow.example.com'"
    )
    op.execute(
        "UPDATE users "
        "SET role = 'TEACHER', department_id = NULL, updated_at = NOW() "
        "WHERE email = 'test@example.com'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users "
        "SET role = 'EXECUTIVE_BOARD', updated_at = NOW() "
        "WHERE email = 'test@example.com'"
    )
    op.execute(
        "UPDATE users "
        "SET name = '최민규', login_id = '최민규', updated_at = NOW() "
        "WHERE email = '20628@studentflow.example.com'"
    )

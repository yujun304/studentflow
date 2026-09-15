"""clear teachers from editable team-manager assignments

Revision ID: 0028_clear_teacher_managers
Revises: 0027_account_corrections
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028_clear_teacher_managers"
down_revision: str | None = "0027_account_corrections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE community_event_plans AS plan "
        "SET team_manager_id = NULL, updated_at = NOW() "
        "FROM users AS manager "
        "WHERE plan.team_manager_id = manager.id "
        "AND manager.role = 'TEACHER' "
        "AND plan.status IN ('DRAFT', 'CHANGES_REQUESTED', 'REJECTED')"
    )


def downgrade() -> None:
    # Invalid teacher assignments cannot be restored safely without guessing intent.
    pass

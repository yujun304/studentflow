"""add dynamic onboarding workspaces

Revision ID: 0025_dynamic_onboarding
Revises: 0024_required_feedback
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_dynamic_onboarding"
down_revision: str | None = "0024_required_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE users SET onboarding_completed_at = NOW()")
    op.create_table(
        "tutorial_workspaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("simple_task_id", sa.UUID(), nullable=False),
        sa.Column("formation_task_id", sa.UUID(), nullable=False),
        sa.Column("submission_task_id", sa.UUID(), nullable=False),
        sa.Column("notice_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["formation_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notice_id"], ["notices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simple_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_tutorial_workspaces_user_id", "tutorial_workspaces", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_tutorial_workspaces_user_id", table_name="tutorial_workspaces")
    op.drop_table("tutorial_workspaces")
    op.drop_column("users", "onboarding_completed_at")

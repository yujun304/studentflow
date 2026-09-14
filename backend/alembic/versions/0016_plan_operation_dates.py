"""Add selected operation dates to plans and tasks.

Revision ID: 0016_plan_operation_dates
Revises: 0015_plan_assignment_tasks
"""

import sqlalchemy as sa
from alembic import op

revision = "0016_plan_operation_dates"
down_revision = "0015_plan_assignment_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("community_event_plans", sa.Column("operation_dates", sa.JSON(), nullable=True))
    op.add_column("tasks", sa.Column("operation_dates", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "operation_dates")
    op.drop_column("community_event_plans", "operation_dates")

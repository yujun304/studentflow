"""remove community plan proposal deadline

Revision ID: 0020_remove_plan_deadline
Revises: 0019_community_meeting_schedule
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_remove_plan_deadline"
down_revision: str | None = "0019_community_meeting_schedule"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("community_event_plans", "proposal_deadline")


def downgrade() -> None:
    op.add_column(
        "community_event_plans",
        sa.Column("proposal_deadline", sa.DateTime(timezone=True), nullable=True),
    )

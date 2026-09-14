"""add community meeting schedule

Revision ID: 0019_community_meeting_schedule
Revises: 0018_agenda_writer_poster
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_community_meeting_schedule"
down_revision: str | None = "0018_agenda_writer_poster"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("community_posts", sa.Column("meeting_date", sa.Date(), nullable=True))
    op.add_column(
        "community_posts", sa.Column("meeting_time_slot", sa.String(length=20), nullable=True)
    )
    op.add_column("community_posts", sa.Column("meeting_time", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("community_posts", "meeting_time")
    op.drop_column("community_posts", "meeting_time_slot")
    op.drop_column("community_posts", "meeting_date")

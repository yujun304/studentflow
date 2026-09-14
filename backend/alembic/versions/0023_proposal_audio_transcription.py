"""store meeting transcript and transcription provider

Revision ID: 0023_proposal_transcript
Revises: 0022_proposal_workflow
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_proposal_transcript"
down_revision: str | None = "0022_proposal_workflow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("community_event_plans", sa.Column("meeting_transcript", sa.Text()))
    op.add_column(
        "community_event_plans", sa.Column("transcription_provider", sa.String(length=24))
    )


def downgrade() -> None:
    op.drop_column("community_event_plans", "transcription_provider")
    op.drop_column("community_event_plans", "meeting_transcript")

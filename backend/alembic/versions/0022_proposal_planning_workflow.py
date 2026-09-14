"""connect proposals to meeting, review, team, and calendar workflow

Revision ID: 0022_proposal_workflow
Revises: 0021_proposal_collaboration
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_proposal_workflow"
down_revision: str | None = "0021_proposal_collaboration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "proposal_attachments",
        sa.Column("purpose", sa.String(length=32), server_default="GENERAL", nullable=False),
    )
    op.add_column("community_event_plans", sa.Column("brief_plan", sa.JSON()))
    op.add_column(
        "community_event_plans",
        sa.Column(
            "meeting_attachment_id",
            sa.Uuid(),
            sa.ForeignKey("proposal_attachments.id", ondelete="SET NULL"),
        ),
    )
    op.add_column("community_event_plans", sa.Column("meeting_notes", sa.JSON()))
    op.add_column("community_event_plans", sa.Column("final_plan", sa.JSON()))
    op.add_column("community_event_plans", sa.Column("ai_provider", sa.String(length=24)))


def downgrade() -> None:
    op.drop_column("community_event_plans", "ai_provider")
    op.drop_column("community_event_plans", "final_plan")
    op.drop_column("community_event_plans", "meeting_notes")
    op.drop_column("community_event_plans", "meeting_attachment_id")
    op.drop_column("community_event_plans", "brief_plan")
    op.drop_column("proposal_attachments", "purpose")

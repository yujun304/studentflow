"""persist required proposal feedback after thirteen recommendations

Revision ID: 0024_required_feedback
Revises: 0023_proposal_transcript
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_required_feedback"
down_revision: str | None = "0023_proposal_transcript"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "community_posts",
        sa.Column("proposal_feedback_required_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_community_posts_proposal_feedback_required_at",
        "community_posts",
        ["proposal_feedback_required_at"],
    )
    op.execute(
        """
        UPDATE community_posts AS post
        SET proposal_feedback_required_at = NOW()
        WHERE COALESCE(post.test_recommendation_bonus, 0) + (
            SELECT COUNT(*)
            FROM community_recommendations AS recommendation
            WHERE recommendation.post_id = post.id
        ) >= 13
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_community_posts_proposal_feedback_required_at",
        table_name="community_posts",
    )
    op.drop_column("community_posts", "proposal_feedback_required_at")

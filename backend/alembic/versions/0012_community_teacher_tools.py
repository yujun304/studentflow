"""Add a development-only recommendation bonus for teacher testing.

Revision ID: 0012_community_teacher_tools
Revises: 0011_event_execution_workflow
"""

import sqlalchemy as sa

from alembic import op

revision = "0012_community_teacher_tools"
down_revision = "0011_event_execution_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "community_posts",
        sa.Column(
            "test_recommendation_bonus",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("community_posts", "test_recommendation_bonus")

"""Add meeting agenda promotion, plan writer, and optional poster work.

Revision ID: 0018_agenda_writer_poster
Revises: 0017_collaborative_plan_review
"""

import sqlalchemy as sa
from alembic import op


revision = "0018_agenda_writer_poster"
down_revision = "0017_collaborative_plan_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "community_posts",
        sa.Column("agenda_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_posts",
        sa.Column("plan_writer_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_community_posts_agenda_at", "community_posts", ["agenda_at"])
    op.create_index("ix_community_posts_plan_writer_id", "community_posts", ["plan_writer_id"])
    op.create_foreign_key(
        "fk_community_posts_plan_writer_id_users",
        "community_posts",
        "users",
        ["plan_writer_id"],
        ["id"],
    )
    op.add_column(
        "community_event_plans",
        sa.Column("poster_required", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("community_event_plans", "poster_required")
    op.drop_constraint(
        "fk_community_posts_plan_writer_id_users",
        "community_posts",
        type_="foreignkey",
    )
    op.drop_index("ix_community_posts_plan_writer_id", table_name="community_posts")
    op.drop_index("ix_community_posts_agenda_at", table_name="community_posts")
    op.drop_column("community_posts", "plan_writer_id")
    op.drop_column("community_posts", "agenda_at")

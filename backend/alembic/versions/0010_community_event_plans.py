"""Add anonymous community comments and structured event plans.

Revision ID: 0010_community_event_plans
Revises: 0009_event_seed_board
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_community_event_plans"
down_revision = "0009_event_seed_board"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column("is_anonymous", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_table(
        "community_event_plans",
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("target_participants", sa.Text(), nullable=False),
        sa.Column("schedule_plan", sa.Text(), nullable=False),
        sa.Column("location_plan", sa.Text(), nullable=False),
        sa.Column("program_plan", sa.Text(), nullable=False),
        sa.Column("role_plan", sa.Text(), nullable=False),
        sa.Column("budget_plan", sa.Text(), nullable=False),
        sa.Column("safety_plan", sa.Text(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id"),
    )
    op.create_index(
        op.f("ix_community_event_plans_author_id"),
        "community_event_plans",
        ["author_id"],
    )
def downgrade() -> None:
    op.drop_table("community_event_plans")
    op.drop_column("comments", "is_anonymous")

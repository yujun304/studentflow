"""add term-scoped community posts, polls, and votes

Revision ID: 0007_community
Revises: 0006_remove_review_workflow
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_community"
down_revision = "0006_remove_review_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "community_posts",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("kind IN ('DISCUSSION', 'SUGGESTION', 'POLL')", name="ck_community_posts_kind"),
    )
    op.create_index(op.f("ix_community_posts_term_id"), "community_posts", ["term_id"])
    op.create_index(op.f("ix_community_posts_author_id"), "community_posts", ["author_id"])
    op.create_index(op.f("ix_community_posts_kind"), "community_posts", ["kind"])

    op.create_table(
        "community_poll_options",
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "position"),
    )
    op.create_index(op.f("ix_community_poll_options_post_id"), "community_poll_options", ["post_id"])

    op.create_table(
        "community_poll_votes",
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("option_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["option_id"], ["community_poll_options.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id"),
    )
    op.create_index(op.f("ix_community_poll_votes_post_id"), "community_poll_votes", ["post_id"])
    op.create_index(op.f("ix_community_poll_votes_option_id"), "community_poll_votes", ["option_id"])
    op.create_index(op.f("ix_community_poll_votes_user_id"), "community_poll_votes", ["user_id"])


def downgrade() -> None:
    op.drop_table("community_poll_votes")
    op.drop_table("community_poll_options")
    op.drop_table("community_posts")

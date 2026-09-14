"""add proposal versions, typed feedback, summaries, and attachments

Revision ID: 0021_proposal_collaboration
Revises: 0020_remove_plan_deadline
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_proposal_collaboration"
down_revision: str | None = "0020_remove_plan_deadline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "community_posts",
        sa.Column("proposal_status", sa.String(length=24), server_default="DISCUSSING", nullable=False),
    )
    op.add_column("community_posts", sa.Column("proposal_topic", sa.String(length=160)))
    op.add_column(
        "community_posts",
        sa.Column("current_proposal_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_index("ix_community_posts_proposal_status", "community_posts", ["proposal_status"])

    op.create_table(
        "proposal_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("post_id", sa.Uuid(), sa.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=160)),
        sa.Column("change_summary", sa.String(length=500)),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("post_id", "version_number"),
    )
    op.create_index("ix_proposal_versions_post_id", "proposal_versions", ["post_id"])
    op.create_index("ix_proposal_versions_author_id", "proposal_versions", ["author_id"])
    op.execute(
        sa.text(
            """
            INSERT INTO proposal_versions
                (id, post_id, version_number, title, description, change_summary, author_id, created_at)
            SELECT gen_random_uuid(), id, 1, title, content, '기존 제안에서 가져옴', author_id, created_at
            FROM community_posts
            """
        )
    )

    op.create_table(
        "proposal_feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("post_id", sa.Uuid(), sa.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposal_version_id", sa.Uuid(), sa.ForeignKey("proposal_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("post_id", "author_id", "idempotency_key"),
    )
    for column in ("post_id", "proposal_version_id", "author_id", "category", "deleted_at"):
        op.create_index(f"ix_proposal_feedback_{column}", "proposal_feedback", [column])

    op.create_table(
        "proposal_summaries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("proposal_version_id", sa.Uuid(), sa.ForeignKey("proposal_versions.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("concerns", sa.JSON(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("new_ideas", sa.JSON(), nullable=False),
        sa.Column("open_questions", sa.JSON(), nullable=False),
        sa.Column("source_feedback_updated_at", sa.DateTime(timezone=True)),
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "proposal_attachments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("proposal_version_id", sa.Uuid(), sa.ForeignKey("proposal_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=255), unique=True, nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_proposal_attachments_proposal_version_id", "proposal_attachments", ["proposal_version_id"])


def downgrade() -> None:
    op.drop_table("proposal_attachments")
    op.drop_table("proposal_summaries")
    op.drop_table("proposal_feedback")
    op.drop_table("proposal_versions")
    op.drop_index("ix_community_posts_proposal_status", table_name="community_posts")
    op.drop_column("community_posts", "current_proposal_version")
    op.drop_column("community_posts", "proposal_topic")
    op.drop_column("community_posts", "proposal_status")

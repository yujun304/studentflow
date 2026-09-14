"""Turn community posts into an anonymous, star-ranked event seed board.

Revision ID: 0009_event_seed_board
Revises: 0008_operations_refinement
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_event_seed_board"
down_revision = "0008_operations_refinement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "community_posts",
        sa.Column("is_anonymous", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("community_posts", sa.Column("converted_event_id", sa.UUID(), nullable=True))
    op.add_column(
        "community_posts", sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("community_posts", sa.Column("converted_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_community_posts_converted_event",
        "community_posts",
        "events",
        ["converted_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_community_posts_converted_by",
        "community_posts",
        "users",
        ["converted_by"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_community_posts_converted_event_id", "community_posts", ["converted_event_id"]
    )

    op.create_table(
        "community_recommendations",
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id"),
    )
    op.create_index(
        op.f("ix_community_recommendations_post_id"),
        "community_recommendations",
        ["post_id"],
    )
    op.create_index(
        op.f("ix_community_recommendations_user_id"),
        "community_recommendations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_table("community_recommendations")
    op.drop_constraint("uq_community_posts_converted_event_id", "community_posts", type_="unique")
    op.drop_constraint("fk_community_posts_converted_by", "community_posts", type_="foreignkey")
    op.drop_constraint("fk_community_posts_converted_event", "community_posts", type_="foreignkey")
    op.drop_column("community_posts", "converted_by")
    op.drop_column("community_posts", "converted_at")
    op.drop_column("community_posts", "converted_event_id")
    op.drop_column("community_posts", "is_anonymous")

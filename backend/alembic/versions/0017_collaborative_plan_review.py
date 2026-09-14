"""Add collaborative editing and teacher review to community plans.

Revision ID: 0017_collaborative_plan_review
Revises: 0016_plan_operation_dates
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_collaborative_plan_review"
down_revision = "0016_plan_operation_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        "purpose",
        "target_participants",
        "schedule_plan",
        "location_plan",
        "program_plan",
        "role_plan",
        "budget_plan",
        "safety_plan",
    ):
        op.alter_column("community_event_plans", column, existing_type=sa.Text(), nullable=True)

    op.add_column(
        "community_event_plans",
        sa.Column("status", sa.String(length=24), nullable=False, server_default="DRAFT"),
    )
    op.add_column(
        "community_event_plans",
        sa.Column("proposal_deadline", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_event_plans",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "community_event_plans",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_event_plans",
        sa.Column("submitted_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "community_event_plans",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_event_plans",
        sa.Column("approved_by", sa.Uuid(), nullable=True),
    )
    op.add_column("community_event_plans", sa.Column("review_note", sa.Text(), nullable=True))
    op.create_index("ix_community_event_plans_status", "community_event_plans", ["status"])
    op.create_foreign_key(
        "fk_community_event_plans_submitted_by_users",
        "community_event_plans",
        "users",
        ["submitted_by"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_community_event_plans_approved_by_users",
        "community_event_plans",
        "users",
        ["approved_by"],
        ["id"],
    )

    op.create_table(
        "community_plan_revisions",
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("editor_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["editor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["community_event_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "version"),
    )
    op.create_index("ix_community_plan_revisions_plan_id", "community_plan_revisions", ["plan_id"])
    op.create_index("ix_community_plan_revisions_editor_id", "community_plan_revisions", ["editor_id"])

    op.create_table(
        "community_plan_suggestions",
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("section", sa.String(length=40), nullable=False),
        sa.Column("proposed_content", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["community_event_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_community_plan_suggestions_plan_id", "community_plan_suggestions", ["plan_id"])
    op.create_index("ix_community_plan_suggestions_author_id", "community_plan_suggestions", ["author_id"])
    op.create_index("ix_community_plan_suggestions_status", "community_plan_suggestions", ["status"])


def downgrade() -> None:
    op.drop_table("community_plan_suggestions")
    op.drop_table("community_plan_revisions")
    op.drop_constraint(
        "fk_community_event_plans_approved_by_users",
        "community_event_plans",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_community_event_plans_submitted_by_users",
        "community_event_plans",
        type_="foreignkey",
    )
    op.drop_index("ix_community_event_plans_status", table_name="community_event_plans")
    for column in (
        "review_note",
        "approved_by",
        "approved_at",
        "submitted_by",
        "submitted_at",
        "version",
        "proposal_deadline",
        "status",
    ):
        op.drop_column("community_event_plans", column)

    for column in (
        "safety_plan",
        "budget_plan",
        "role_plan",
        "program_plan",
        "location_plan",
        "schedule_plan",
        "target_participants",
        "purpose",
    ):
        op.alter_column("community_event_plans", column, existing_type=sa.Text(), nullable=False)

"""Add structured team formations and calendar reminder metadata.

Revision ID: 0002_team_calendar
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_team_calendar"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_type ADD VALUE IF NOT EXISTS 'TEAM_FORMATION'")
    op.add_column("teams", sa.Column("submission_id", sa.UUID(), nullable=True))
    op.add_column("teams", sa.Column("created_by", sa.UUID(), nullable=True))
    op.add_column("teams", sa.Column("role_description", sa.String(length=200), nullable=True))
    op.add_column("teams", sa.Column("schedule_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("teams", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_teams_submission_id_submissions", "teams", "submissions", ["submission_id"], ["id"]
    )
    op.create_foreign_key("fk_teams_created_by_users", "teams", "users", ["created_by"], ["id"])
    op.create_index(op.f("ix_teams_submission_id"), "teams", ["submission_id"], unique=False)
    op.create_index(op.f("ix_teams_created_by"), "teams", ["created_by"], unique=False)
    op.create_index(op.f("ix_teams_schedule_at"), "teams", ["schedule_at"], unique=False)
    op.create_index(op.f("ix_teams_approved_at"), "teams", ["approved_at"], unique=False)

    op.add_column(
        "reminders",
        sa.Column("category", sa.String(length=40), server_default="PERSONAL", nullable=False),
    )
    op.add_column(
        "reminders",
        sa.Column("color", sa.String(length=20), server_default="#356ae6", nullable=False),
    )
    op.add_column("reminders", sa.Column("source_type", sa.String(length=40), nullable=True))
    op.add_column("reminders", sa.Column("source_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_reminders_category"), "reminders", ["category"], unique=False)
    op.create_index(op.f("ix_reminders_source_type"), "reminders", ["source_type"], unique=False)
    op.create_index(op.f("ix_reminders_source_id"), "reminders", ["source_id"], unique=False)
    op.create_unique_constraint(
        "uq_reminders_user_source", "reminders", ["user_id", "source_type", "source_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_reminders_user_source", "reminders", type_="unique")
    op.drop_index(op.f("ix_reminders_source_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_source_type"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_category"), table_name="reminders")
    op.drop_column("reminders", "source_id")
    op.drop_column("reminders", "source_type")
    op.drop_column("reminders", "color")
    op.drop_column("reminders", "category")

    op.drop_index(op.f("ix_teams_approved_at"), table_name="teams")
    op.drop_index(op.f("ix_teams_schedule_at"), table_name="teams")
    op.drop_index(op.f("ix_teams_submission_id"), table_name="teams")
    op.drop_index(op.f("ix_teams_created_by"), table_name="teams")
    op.drop_constraint("fk_teams_created_by_users", "teams", type_="foreignkey")
    op.drop_constraint("fk_teams_submission_id_submissions", "teams", type_="foreignkey")
    op.drop_column("teams", "approved_at")
    op.drop_column("teams", "schedule_at")
    op.drop_column("teams", "role_description")
    op.drop_column("teams", "created_by")
    op.drop_column("teams", "submission_id")
    # PostgreSQL enum values are intentionally retained on downgrade to avoid rebuilding task_type.

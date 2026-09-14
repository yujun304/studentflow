"""Assign execution managers to community event plans.

Revision ID: 0011_event_execution_workflow
Revises: 0010_community_event_plans
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_event_execution_workflow"
down_revision = "0010_community_event_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "community_event_plans",
        sa.Column("team_manager_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "community_event_plans",
        sa.Column("poster_manager_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_community_event_plans_team_manager_id_users",
        "community_event_plans",
        "users",
        ["team_manager_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_community_event_plans_poster_manager_id_users",
        "community_event_plans",
        "users",
        ["poster_manager_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_community_event_plans_team_manager_id"),
        "community_event_plans",
        ["team_manager_id"],
    )
    op.create_index(
        op.f("ix_community_event_plans_poster_manager_id"),
        "community_event_plans",
        ["poster_manager_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_community_event_plans_poster_manager_id"),
        table_name="community_event_plans",
    )
    op.drop_index(
        op.f("ix_community_event_plans_team_manager_id"),
        table_name="community_event_plans",
    )
    op.drop_constraint(
        "fk_community_event_plans_poster_manager_id_users",
        "community_event_plans",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_community_event_plans_team_manager_id_users",
        "community_event_plans",
        type_="foreignkey",
    )
    op.drop_column("community_event_plans", "poster_manager_id")
    op.drop_column("community_event_plans", "team_manager_id")

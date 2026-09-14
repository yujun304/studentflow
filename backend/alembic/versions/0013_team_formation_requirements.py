"""Add structured team formation requirements.

Revision ID: 0013_team_formation_requirements
Revises: 0012_community_teacher_tools
"""

import sqlalchemy as sa
from alembic import op

revision = "0013_team_formation_requirements"
down_revision = "0012_community_teacher_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("community_event_plans", "tasks"):
        op.add_column(table, sa.Column("operation_days", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("teams_per_day", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("people_per_team", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("team_role_description", sa.String(500), nullable=True))


def downgrade() -> None:
    for table in ("tasks", "community_event_plans"):
        op.drop_column(table, "team_role_description")
        op.drop_column(table, "people_per_team")
        op.drop_column(table, "teams_per_day")
        op.drop_column(table, "operation_days")

"""Add per-team requirements.

Revision ID: 0014_per_team_requirements
Revises: 0013_team_formation_requirements
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_per_team_requirements"
down_revision = "0013_team_formation_requirements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("community_event_plans", sa.Column("team_requirements", sa.JSON(), nullable=True))
    op.add_column("tasks", sa.Column("team_requirements", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "team_requirements")
    op.drop_column("community_event_plans", "team_requirements")

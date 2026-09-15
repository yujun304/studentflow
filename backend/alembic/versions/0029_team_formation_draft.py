"""store automatic team formation drafts

Revision ID: 0029_team_formation_draft
Revises: 0028_clear_teacher_managers
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_team_formation_draft"
down_revision: str | None = "0028_clear_teacher_managers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("formation_draft", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "formation_draft")

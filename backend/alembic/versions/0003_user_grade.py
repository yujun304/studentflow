"""Add the student grade attribute.

Revision ID: 0003_user_grade
Revises: 0002_team_calendar
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_user_grade"
down_revision = "0002_team_calendar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("grade", sa.Integer(), nullable=True))
    op.create_check_constraint("ck_users_grade", "users", "grade IS NULL OR grade BETWEEN 1 AND 3")
    op.create_index(op.f("ix_users_grade"), "users", ["grade"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_grade"), table_name="users")
    op.drop_constraint("ck_users_grade", "users", type_="check")
    op.drop_column("users", "grade")

"""Add floor maps, ordering, and event completion records.

Revision ID: 0008_operations_refinement
Revises: 0007_community
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_operations_refinement"
down_revision = "0007_community"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "school_maps",
        sa.Column("floor_label", sa.String(length=80), server_default="1층", nullable=False),
    )
    op.add_column(
        "school_maps",
        sa.Column("floor_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "event_completion_records",
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("outcomes", sa.Text(), nullable=True),
        sa.Column("incidents", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("attendee_count", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("handover_guide_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attendee_count IS NULL OR attendee_count >= 0",
            name="ck_event_completion_attendee_count",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["handover_guide_id"], ["handover_guides.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint("handover_guide_id"),
    )
    op.create_index(
        op.f("ix_event_completion_records_event_id"),
        "event_completion_records",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_event_completion_records_completed_at"),
        "event_completion_records",
        ["completed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_event_completion_records_completed_at"),
        table_name="event_completion_records",
    )
    op.drop_index(
        op.f("ix_event_completion_records_event_id"),
        table_name="event_completion_records",
    )
    op.drop_table("event_completion_records")
    op.drop_column("school_maps", "floor_order")
    op.drop_column("school_maps", "floor_label")

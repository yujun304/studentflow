"""Add decision, handover, event operations, and school map features.

Revision ID: 0005_operations_center
Revises: 0004_remove_chat
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_operations_center"
down_revision = "0004_remove_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    decision_status = postgresql.ENUM("OPEN", "DONE", "CANCELLED", name="decision_status")
    run_item_status = postgresql.ENUM(
        "PLANNED", "READY", "IN_PROGRESS", "DONE", "ISSUE", name="run_item_status"
    )
    op.create_table(
        "decision_cards",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("meeting_record_id", sa.UUID(), nullable=True),
        sa.Column("event_id", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", decision_status, nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["meeting_record_id"], ["meeting_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index(op.f("ix_decision_cards_term_id"), "decision_cards", ["term_id"])
    op.create_index(op.f("ix_decision_cards_meeting_record_id"), "decision_cards", ["meeting_record_id"])
    op.create_index(op.f("ix_decision_cards_event_id"), "decision_cards", ["event_id"])
    op.create_index(op.f("ix_decision_cards_owner_id"), "decision_cards", ["owner_id"])
    op.create_index(op.f("ix_decision_cards_due_at"), "decision_cards", ["due_at"])

    op.create_table(
        "handover_guides",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("what_worked", sa.Text(), nullable=True),
        sa.Column("pitfalls", sa.Text(), nullable=True),
        sa.Column("checklist", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_handover_guides_term_id"), "handover_guides", ["term_id"])
    op.create_index(op.f("ix_handover_guides_event_id"), "handover_guides", ["event_id"])
    op.create_index(op.f("ix_handover_guides_published_at"), "handover_guides", ["published_at"])

    op.create_table(
        "event_run_items",
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("planned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location_label", sa.String(length=200), nullable=True),
        sa.Column("assignee_id", sa.UUID(), nullable=True),
        sa.Column("status", run_item_status, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_run_items_event_id"), "event_run_items", ["event_id"])
    op.create_index(op.f("ix_event_run_items_planned_at"), "event_run_items", ["planned_at"])
    op.create_index(op.f("ix_event_run_items_assignee_id"), "event_run_items", ["assignee_id"])

    op.create_table(
        "school_maps",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"]),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id"),
    )
    op.create_index(op.f("ix_school_maps_term_id"), "school_maps", ["term_id"])
    op.create_index(op.f("ix_school_maps_event_id"), "school_maps", ["event_id"])

    op.create_table(
        "map_assignments",
        sa.Column("map_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("activity", sa.String(length=300), nullable=False),
        sa.Column("x_ratio", sa.Float(), nullable=False),
        sa.Column("y_ratio", sa.Float(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("x_ratio >= 0 AND x_ratio <= 1", name="ck_map_assignment_x"),
        sa.CheckConstraint("y_ratio >= 0 AND y_ratio <= 1", name="ck_map_assignment_y"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["map_id"], ["school_maps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_map_assignments_map_id"), "map_assignments", ["map_id"])
    op.create_index(op.f("ix_map_assignments_user_id"), "map_assignments", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_map_assignments_user_id"), table_name="map_assignments")
    op.drop_index(op.f("ix_map_assignments_map_id"), table_name="map_assignments")
    op.drop_table("map_assignments")
    op.drop_index(op.f("ix_school_maps_event_id"), table_name="school_maps")
    op.drop_index(op.f("ix_school_maps_term_id"), table_name="school_maps")
    op.drop_table("school_maps")
    op.drop_index(op.f("ix_event_run_items_assignee_id"), table_name="event_run_items")
    op.drop_index(op.f("ix_event_run_items_planned_at"), table_name="event_run_items")
    op.drop_index(op.f("ix_event_run_items_event_id"), table_name="event_run_items")
    op.drop_table("event_run_items")
    op.drop_index(op.f("ix_handover_guides_published_at"), table_name="handover_guides")
    op.drop_index(op.f("ix_handover_guides_event_id"), table_name="handover_guides")
    op.drop_index(op.f("ix_handover_guides_term_id"), table_name="handover_guides")
    op.drop_table("handover_guides")
    op.drop_index(op.f("ix_decision_cards_due_at"), table_name="decision_cards")
    op.drop_index(op.f("ix_decision_cards_owner_id"), table_name="decision_cards")
    op.drop_index(op.f("ix_decision_cards_event_id"), table_name="decision_cards")
    op.drop_index(op.f("ix_decision_cards_meeting_record_id"), table_name="decision_cards")
    op.drop_index(op.f("ix_decision_cards_term_id"), table_name="decision_cards")
    op.drop_table("decision_cards")
    postgresql.ENUM(name="run_item_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="decision_status").drop(op.get_bind(), checkfirst=True)

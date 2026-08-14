"""Remove the chat feature.

Revision ID: 0004_remove_chat
Revises: 0003_user_grade
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_remove_chat"
down_revision = "0003_user_grade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f("ix_files_chat_message_id"), table_name="files")
    op.drop_constraint("files_chat_message_id_fkey", "files", type_="foreignkey")
    op.drop_column("files", "chat_message_id")

    op.drop_index(op.f("ix_message_reads_user_id"), table_name="message_reads")
    op.drop_table("message_reads")
    op.drop_index(op.f("ix_chat_participants_user_id"), table_name="chat_participants")
    op.drop_index(op.f("ix_chat_participants_room_id"), table_name="chat_participants")
    op.drop_table("chat_participants")
    op.drop_index(op.f("ix_chat_messages_room_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_created_at"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_author_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index(op.f("ix_chat_rooms_term_id"), table_name="chat_rooms")
    op.drop_table("chat_rooms")
    op.execute("DROP TYPE chat_room_type")


def downgrade() -> None:
    chat_room_type = postgresql.ENUM(
        "ALL", "DEPARTMENT", "GROUP", "DIRECT", name="chat_room_type", create_type=False
    )
    chat_room_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "chat_rooms",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("type", chat_room_type, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=True),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_rooms_term_id"), "chat_rooms", ["term_id"], unique=False)
    op.create_table(
        "chat_messages",
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("reply_to_id", sa.UUID(), nullable=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reply_to_id"], ["chat_messages.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "sequence"),
    )
    op.create_index(
        op.f("ix_chat_messages_author_id"), "chat_messages", ["author_id"], unique=False
    )
    op.create_index(
        op.f("ix_chat_messages_created_at"), "chat_messages", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_chat_messages_room_id"), "chat_messages", ["room_id"], unique=False)
    op.create_table(
        "chat_participants",
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "user_id"),
    )
    op.create_index(
        op.f("ix_chat_participants_room_id"), "chat_participants", ["room_id"], unique=False
    )
    op.create_index(
        op.f("ix_chat_participants_user_id"), "chat_participants", ["user_id"], unique=False
    )
    op.create_table(
        "message_reads",
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "read_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id"),
    )
    op.create_index(op.f("ix_message_reads_user_id"), "message_reads", ["user_id"], unique=False)
    op.add_column("files", sa.Column("chat_message_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "files_chat_message_id_fkey", "files", "chat_messages", ["chat_message_id"], ["id"]
    )
    op.create_index(op.f("ix_files_chat_message_id"), "files", ["chat_message_id"], unique=False)

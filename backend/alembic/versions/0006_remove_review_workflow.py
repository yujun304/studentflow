"""remove task review workflow and normalize legacy rows

Revision ID: 0006_remove_review_workflow
Revises: 0005_operations_center
"""

from alembic import op

revision = "0006_remove_review_workflow"
down_revision = "0005_operations_center"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE tasks SET status = 'DONE' WHERE status = 'REVIEW'")
    op.execute("UPDATE tasks SET status = 'TODO' WHERE status = 'REJECTED'")
    op.execute(
        "UPDATE submissions SET status = 'APPROVED', rejection_reason = NULL "
        "WHERE status IN ('SUBMITTED', 'REJECTED')"
    )
    op.execute(
        "UPDATE teams SET approved_at = CURRENT_TIMESTAMP "
        "WHERE submission_id IS NOT NULL AND approved_at IS NULL"
    )


def downgrade() -> None:
    # 검토 대기와 반려 상태는 어느 행이었는지 복원할 수 없어 데이터 상태는 유지한다.
    pass

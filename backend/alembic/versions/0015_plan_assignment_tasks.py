"""Link plan assignments to pending tasks.

Revision ID: 0015_plan_assignment_tasks
Revises: 0014_per_team_requirements
"""

import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0015_plan_assignment_tasks"
down_revision = "0014_per_team_requirements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("community_event_plans", sa.Column("team_task_id", sa.UUID(), nullable=True))
    op.add_column("community_event_plans", sa.Column("poster_task_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_plan_team_task", "community_event_plans", "tasks", ["team_task_id"], ["id"])
    op.create_foreign_key("fk_plan_poster_task", "community_event_plans", "tasks", ["poster_task_id"], ["id"])
    connection = op.get_bind()
    plans = connection.execute(
        sa.text(
            """
            SELECT p.id, p.author_id, p.team_manager_id, p.poster_manager_id,
                   p.operation_days, p.teams_per_day, p.people_per_team,
                   p.team_role_description, p.team_requirements, cp.title, u.term_id
            FROM community_event_plans p
            JOIN community_posts cp ON cp.id = p.post_id
            JOIN users u ON u.id = p.author_id
            WHERE p.team_task_id IS NULL AND p.poster_task_id IS NULL
            """
        )
    ).mappings()
    for plan in plans:
        team_task_id = uuid.uuid4()
        poster_task_id = uuid.uuid4()
        common = {"term_id": plan["term_id"], "created_by": plan["author_id"]}
        connection.execute(
            sa.text(
                """
                INSERT INTO tasks (
                    id, term_id, title, description, type, status, created_by,
                    operation_days, teams_per_day, people_per_team,
                    team_role_description, team_requirements, created_at, updated_at
                ) VALUES (
                    :id, :term_id, :title, :description, 'TEAM_FORMATION', 'TODO', :created_by,
                    :operation_days, :teams_per_day, :people_per_team,
                    :team_role_description, CAST(:team_requirements AS JSON), now(), now()
                )
                """
            ),
            {
                **common,
                "id": team_task_id,
                "title": f"{plan['title']} 조 편성",
                "description": "행사 확정 전 담당 예정 업무입니다. 기획서의 조별 인원과 역할을 확인해 주세요.",
                "operation_days": plan["operation_days"],
                "teams_per_day": plan["teams_per_day"],
                "people_per_team": plan["people_per_team"],
                "team_role_description": plan["team_role_description"],
                "team_requirements": json.dumps(plan["team_requirements"], ensure_ascii=False),
            },
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO tasks (id, term_id, title, description, type, status, created_by, created_at, updated_at)
                VALUES (:id, :term_id, :title, :description, 'SUBMISSION', 'TODO', :created_by, now(), now())
                """
            ),
            {
                **common,
                "id": poster_task_id,
                "title": f"{plan['title']} 포스터 제출",
                "description": "행사 확정 전 담당 예정 업무입니다. 기획서를 확인하고 포스터를 준비해 주세요.",
            },
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO task_assignees (id, task_id, user_id)
                VALUES (:team_assignee_id, :team_task_id, :team_manager_id),
                       (:poster_assignee_id, :poster_task_id, :poster_manager_id)
                """
            ),
            {
                "team_assignee_id": uuid.uuid4(),
                "team_task_id": team_task_id,
                "team_manager_id": plan["team_manager_id"],
                "poster_assignee_id": uuid.uuid4(),
                "poster_task_id": poster_task_id,
                "poster_manager_id": plan["poster_manager_id"],
            },
        )
        connection.execute(
            sa.text(
                "UPDATE community_event_plans SET team_task_id=:team_task_id, poster_task_id=:poster_task_id WHERE id=:plan_id"
            ),
            {"team_task_id": team_task_id, "poster_task_id": poster_task_id, "plan_id": plan["id"]},
        )


def downgrade() -> None:
    op.drop_constraint("fk_plan_poster_task", "community_event_plans", type_="foreignkey")
    op.drop_constraint("fk_plan_team_task", "community_event_plans", type_="foreignkey")
    op.drop_column("community_event_plans", "poster_task_id")
    op.drop_column("community_event_plans", "team_task_id")

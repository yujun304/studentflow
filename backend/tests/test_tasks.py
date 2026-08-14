from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.tasks import list_tasks, pending_submissions, update_task
from app.core.database import Base
from app.models.entities import (
    Role,
    Submission,
    SubmissionStatus,
    SubmissionVersion,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    Term,
    User,
)
from app.schemas import TaskUpdate


@pytest.mark.asyncio
async def test_assigned_task_and_latest_pending_submission_are_returned():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="테스트 기수",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        teacher = User(
            email="teacher@example.com",
            name="선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        member = User(
            email="member@example.com",
            name="학생",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([teacher, member])
        await db.flush()
        task = Task(
            term_id=term.id,
            title="계획서 제출",
            type=TaskType.SUBMISSION,
            status=TaskStatus.REVIEW,
            created_by=teacher.id,
        )
        db.add(task)
        await db.flush()
        db.add(TaskAssignee(task_id=task.id, user_id=member.id))
        submission = Submission(
            task_id=task.id,
            submitted_by=member.id,
            status=SubmissionStatus.SUBMITTED,
        )
        db.add(submission)
        await db.flush()
        db.add_all(
            [
                SubmissionVersion(submission_id=submission.id, version=1, content="초안"),
                SubmissionVersion(submission_id=submission.id, version=2, content="최종안"),
            ]
        )
        await db.commit()

        tasks = await list_tasks(member, db)
        assert len(tasks) == 1
        assert tasks[0].assigned_to_me is True

        reviews = await pending_submissions(teacher, db)
        assert len(reviews) == 1
        assert reviews[0].submitted_by_name == "학생"
        assert reviews[0].version == 2
        assert reviews[0].content == "최종안"

        updated = await update_task(
            task.id,
            TaskUpdate(title="계획서 최종 제출", assignee_ids=[teacher.id]),
            teacher,
            db,
        )
        assert updated.title == "계획서 최종 제출"
        assert updated.assignee_ids == [teacher.id]
        assert updated.can_edit is True

    await engine.dispose()

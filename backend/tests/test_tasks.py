from datetime import date
from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.tasks import (
    delete_task,
    list_task_submissions,
    list_tasks,
    update_task,
    upload_file,
)
from app.api.tasks import storage as task_storage
from app.api.tasks import submit as submit_task
from app.core.database import Base
from app.models.entities import (
    Event,
    EventType,
    Notification,
    Role,
    Submission,
    SubmissionStatus,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    Term,
    User,
)
from app.schemas import SubmissionIn, TaskUpdate


@pytest.mark.asyncio
async def test_assigned_submission_task_completes_after_file_and_notifies_teacher(monkeypatch):
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
        event = Event(
            term_id=term.id,
            title="학교 축제",
            type=EventType.EVENT,
            event_date=date(2026, 9, 1),
            manager_id=teacher.id,
        )
        db.add(event)
        await db.flush()
        task = Task(
            term_id=term.id,
            event_id=event.id,
            title="학교 축제 포스터 제출",
            type=TaskType.SUBMISSION,
            status=TaskStatus.TODO,
            created_by=teacher.id,
        )
        db.add(task)
        await db.flush()
        db.add(TaskAssignee(task_id=task.id, user_id=member.id))
        await db.commit()

        tasks = await list_tasks(member, db)
        assert len(tasks) == 1
        assert tasks[0].assigned_to_me is True

        version = await submit_task(task.id, SubmissionIn(content="포스터 최종안"), member, db)
        await db.refresh(task)
        assert task.status == TaskStatus.IN_PROGRESS
        submission = await db.scalar(select(Submission).where(Submission.task_id == task.id))
        assert submission is not None
        assert submission.status == SubmissionStatus.SUBMITTED

        async def fake_save(_upload):
            return "test/poster.png", 2048

        monkeypatch.setattr(task_storage, "save", fake_save)
        uploaded = await upload_file(
            version.id,
            UploadFile(filename="축제-포스터.png", file=BytesIO(b"poster")),
            member,
            db,
        )
        assert uploaded.original_name == "축제-포스터.png"
        await db.refresh(task)
        await db.refresh(submission)
        assert task.status == TaskStatus.DONE
        assert submission.status == SubmissionStatus.APPROVED
        teacher_view = await list_task_submissions(task.id, teacher, db)
        assert teacher_view[0].files[0].original_name == "축제-포스터.png"
        notification = await db.scalar(
            select(Notification).where(Notification.user_id == teacher.id)
        )
        assert notification is not None
        assert notification.type == "POSTER_SUBMITTED"

        updated = await update_task(
            task.id,
            TaskUpdate(title="계획서 최종 제출", assignee_ids=[teacher.id]),
            teacher,
            db,
        )
        assert updated.title == "계획서 최종 제출"
        assert updated.assignee_ids == [teacher.id]
        assert updated.can_edit is True

        deletable = Task(
            term_id=term.id,
            title="독립 삭제 검사 업무",
            type=TaskType.SIMPLE,
            status=TaskStatus.TODO,
            created_by=teacher.id,
        )
        db.add(deletable)
        await db.commit()
        await delete_task(deletable.id, teacher, db)
        assert await db.get(Task, deletable.id) is None

    await engine.dispose()

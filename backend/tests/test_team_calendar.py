import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.calendar import (
    calendar_items,
    create_calendar_item,
    delete_calendar_item,
    update_calendar_item,
)
from app.api.tasks import pending_submissions, review, submit_team_formation
from app.core.database import Base
from app.models.entities import (
    Event,
    EventParticipant,
    EventType,
    Reminder,
    Role,
    SubmissionStatus,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    Term,
    User,
)
from app.schemas import (
    CalendarItemIn,
    CalendarItemUpdate,
    ReviewIn,
    TeamDraftIn,
    TeamFormationIn,
)


@pytest.mark.asyncio
async def test_team_approval_creates_member_calendar_reminder_and_personal_items_are_editable():
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
        submitter = User(
            email="submitter@example.com",
            name="편성 담당",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        member = User(
            email="member@example.com",
            name="조원",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([teacher, submitter, member])
        await db.flush()
        event = Event(
            term_id=term.id,
            title="축제",
            type=EventType.EVENT,
            event_date=date(2026, 7, 28),
            manager_id=teacher.id,
        )
        db.add(event)
        await db.flush()
        task = Task(
            term_id=term.id,
            event_id=event.id,
            title="축제 조 편성",
            type=TaskType.TEAM_FORMATION,
            status=TaskStatus.TODO,
            due_at=datetime(2026, 7, 25, 9, tzinfo=UTC),
            created_by=teacher.id,
        )
        db.add(task)
        await db.flush()
        db.add(TaskAssignee(task_id=task.id, user_id=submitter.id))
        await db.commit()

        version = await submit_team_formation(
            task.id,
            TeamFormationIn(
                content="축제 안내조 편성안",
                teams=[
                    TeamDraftIn(
                        name="안내 1조",
                        role_description="정문 안내",
                        leader_id=submitter.id,
                        member_ids=[submitter.id, member.id],
                        schedule_at=datetime(2026, 7, 28, 1, tzinfo=UTC),
                    )
                ],
            ),
            submitter,
            db,
        )
        pending = await pending_submissions(teacher, db)
        assert pending[0].version_id == version.id
        assert pending[0].teams[0].name == "안내 1조"
        assert set(pending[0].teams[0].member_names) == {"편성 담당", "조원"}

        await review(
            pending[0].id,
            ReviewIn(status=SubmissionStatus.APPROVED),
            teacher,
            db,
        )
        reminder = await db.scalar(
            select(Reminder).where(Reminder.user_id == member.id, Reminder.category == "TEAM")
        )
        assert reminder is not None
        assert reminder.title == "[조 일정] 안내 1조"
        assert await db.scalar(
            select(EventParticipant.id).where(
                EventParticipant.event_id == event.id,
                EventParticipant.user_id == member.id,
            )
        )

        items = await calendar_items(date(2026, 7, 1), date(2026, 8, 31), member, db)
        assert any(
            item.source == "TEAM_REMINDER" and item.title.endswith("안내 1조") for item in items
        )

        personal = await create_calendar_item(
            CalendarItemIn(
                title="개인 준비",
                starts_at=datetime(2026, 7, 29, 3, tzinfo=UTC),
                color="#db2777",
            ),
            member,
            db,
        )
        personal_id = uuid.UUID(personal.id)
        edited = await update_calendar_item(
            personal_id,
            CalendarItemUpdate(title="개인 준비물 확인"),
            member,
            db,
        )
        assert edited.title == "개인 준비물 확인"
        await delete_calendar_item(personal_id, member, db)
        assert await db.get(Reminder, personal_id) is None

    await engine.dispose()

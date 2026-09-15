from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.events import create_teacher_event, delete_event, list_events, update_event
from app.core.database import Base
from app.models.entities import (
    Event,
    EventParticipant,
    EventType,
    Notification,
    Role,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    Term,
    User,
)
from app.schemas import EventUpdate, TeacherEventCreateIn, TeamRequirementIn


@pytest.mark.asyncio
async def test_teacher_event_creation_assigns_complete_team_formation_task():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="교사 행사 제작 테스트",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        teacher = User(
            email="teacher-create@example.com",
            name="담당 선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        manager = User(
            email="formation-manager@example.com",
            name="조 편성 담당",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        participant = User(
            email="event-participant@example.com",
            name="참여 학생",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([teacher, manager, participant])
        await db.commit()

        result = await create_teacher_event(
            TeacherEventCreateIn(
                title="가을 학교 축제",
                type=EventType.EVENT,
                purpose="학생들이 함께 준비하는 축제를 운영합니다.",
                target_participants="전교생",
                schedule_plan="오전 준비, 오후 부스 운영",
                program_plan="안내 부스와 체험 부스를 운영합니다.",
                preparation_plan="안내판과 명찰",
                safety_plan="통로 확보와 비상 연락망 확인",
                location="운동장",
                event_date=date(2026, 10, 16),
                starts_at=time(9, 0),
                ends_at=time(16, 0),
                operation_dates=[date(2026, 10, 16), date(2026, 10, 17)],
                team_requirements=[
                    TeamRequirementIn(
                        name="안내조", people_count=1, role_description="정문 안내"
                    ),
                    TeamRequirementIn(
                        name="운영조", people_count=1, role_description="부스 운영"
                    ),
                ],
                team_manager_id=manager.id,
                participant_ids=[manager.id, participant.id],
                formation_due_at=datetime(2026, 10, 10, 9, tzinfo=UTC),
            ),
            teacher,
            db,
        )

        event = await db.get(Event, result.event_id)
        task = await db.get(Task, result.task_id)
        assert event is not None
        assert "행사 목적\n학생들이 함께 준비" in (event.description or "")
        assert task is not None
        assert task.type == TaskType.TEAM_FORMATION
        assert task.operation_dates == ["2026-10-16", "2026-10-17"]
        assert task.team_requirements[0] == {
            "name": "안내조",
            "people_count": 1,
            "role_description": "정문 안내",
        }
        assert task.formation_draft is not None
        assert len(task.formation_draft) == 4
        assert all(len(draft["member_ids"]) == 1 for draft in task.formation_draft)
        assert {draft["leader_id"] for draft in task.formation_draft} == {
            str(manager.id),
            str(participant.id),
        }
        assert await db.scalar(
            select(TaskAssignee.id).where(
                TaskAssignee.task_id == task.id,
                TaskAssignee.user_id == manager.id,
            )
        )
        participant_ids = set(
            (
                await db.scalars(
                    select(EventParticipant.user_id).where(
                        EventParticipant.event_id == event.id
                    )
                )
            ).all()
        )
        assert participant_ids == {manager.id, participant.id}
        notification = await db.scalar(
            select(Notification).where(
                Notification.user_id == manager.id,
                Notification.type == "TEAM_FORMATION_ASSIGNED",
            )
        )
        assert notification is not None
        assert notification.target_id == task.id

    await engine.dispose()


@pytest.mark.asyncio
async def test_teacher_can_update_and_soft_delete_any_current_term_event():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="행사 관리 테스트",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        teacher = User(
            email="event-admin@example.com",
            name="담당 선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        owner = User(
            email="event-owner@example.com",
            name="행사 담당 학생",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([teacher, owner])
        await db.flush()
        event = Event(
            term_id=term.id,
            title="기존 행사",
            type=EventType.EVENT,
            event_date=date(2026, 9, 1),
            manager_id=owner.id,
            status="PLANNED",
        )
        db.add(event)
        await db.flush()
        task = Task(
            term_id=term.id,
            event_id=event.id,
            title="행사 준비",
            type=TaskType.SIMPLE,
            status=TaskStatus.TODO,
            created_by=owner.id,
        )
        db.add(task)
        await db.commit()

        updated = await update_event(
            event.id,
            EventUpdate(
                title="수정된 행사",
                description="선생님이 수정한 행사 설명",
                location="체육관",
                event_date=date(2026, 9, 2),
            ),
            teacher,
            db,
        )
        assert updated.title == "수정된 행사"
        assert updated.can_manage is True

        await delete_event(event.id, teacher, db)
        await db.refresh(task)
        assert task.status == TaskStatus.DONE
        assert await list_events(teacher, db) == []

    await engine.dispose()

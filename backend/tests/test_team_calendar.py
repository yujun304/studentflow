import uuid
from datetime import UTC, date, datetime, time

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
from app.api.tasks import submit_team_formation
from app.core.database import Base
from app.core.errors import AppError
from app.models.entities import (
    CommunityPost,
    Event,
    EventParticipant,
    EventType,
    Notification,
    Reminder,
    Role,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    Term,
    User,
    Team,
)
from app.schemas import (
    CalendarItemIn,
    CalendarItemUpdate,
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
            operation_days=1,
            operation_dates=["2026-07-28"],
            teams_per_day=1,
            people_per_team=2,
            team_role_description="정문 안내",
            team_requirements=[
                {
                    "name": "안내 1조",
                    "people_count": 2,
                    "role_description": "정문 안내",
                    "operation_dates": ["2026-07-28"],
                }
            ],
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
        assert version.id is not None
        await db.refresh(task)
        assert task.status == TaskStatus.DONE
        saved_team = await db.scalar(select(Team).where(Team.task_id == task.id))
        assert saved_team is not None
        assert saved_team.approved_at is not None
        reminder = await db.scalar(
            select(Reminder).where(Reminder.user_id == member.id, Reminder.category == "TEAM")
        )
        assert reminder is not None
        assert reminder.title == "[조 일정] 안내 1조"
        notification = await db.scalar(
            select(Notification).where(
                Notification.user_id == member.id,
                Notification.type == "TEAM_ASSIGNED",
            )
        )
        assert notification is not None
        assert notification.title == "안내 1조에 배정되었습니다"
        assert "정문 안내" in (notification.content or "")
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


@pytest.mark.asyncio
async def test_team_formation_uses_only_teams_selected_for_each_date():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="날짜별 조 편성 테스트",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        first = User(
            email="date-team-first@example.com",
            name="첫날 담당",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        second = User(
            email="date-team-second@example.com",
            name="둘째날 담당",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([first, second])
        await db.flush()
        task = Task(
            term_id=term.id,
            title="날짜별 조 편성",
            type=TaskType.TEAM_FORMATION,
            status=TaskStatus.TODO,
            operation_days=2,
            operation_dates=["2026-09-25", "2026-09-26"],
            teams_per_day=1,
            people_per_team=1,
            team_role_description="날짜별 운영",
            team_requirements=[
                {
                    "name": "등교조",
                    "people_count": 1,
                    "role_description": "등교 안내",
                    "operation_dates": ["2026-09-25"],
                },
                {
                    "name": "정리조",
                    "people_count": 1,
                    "role_description": "행사 정리",
                    "operation_dates": ["2026-09-26"],
                },
            ],
            created_by=first.id,
        )
        db.add(task)
        await db.flush()
        db.add(TaskAssignee(task_id=task.id, user_id=first.id))
        await db.commit()

        with pytest.raises(AppError) as invalid:
            await submit_team_formation(
                task.id,
                TeamFormationIn(
                    content="잘못된 날짜",
                    teams=[
                        TeamDraftIn(
                            name="정리조",
                            role_description="행사 정리",
                            leader_id=second.id,
                            member_ids=[second.id],
                            schedule_at=datetime(2026, 9, 25, 1, tzinfo=UTC),
                        )
                    ],
                ),
                first,
                db,
            )
        assert invalid.value.code == "unknown_team"

        version = await submit_team_formation(
            task.id,
            TeamFormationIn(
                content="날짜별 조 편성안",
                teams=[
                    TeamDraftIn(
                        name="9월 25일 등교조",
                        role_description="등교 안내",
                        leader_id=first.id,
                        member_ids=[first.id],
                        schedule_at=datetime(2026, 9, 25, 1, tzinfo=UTC),
                    ),
                    TeamDraftIn(
                        name="9월 26일 정리조",
                        role_description="행사 정리",
                        leader_id=second.id,
                        member_ids=[second.id],
                        schedule_at=datetime(2026, 9, 26, 1, tzinfo=UTC),
                    ),
                ],
            ),
            first,
            db,
        )

        assert version.id is not None
        saved = list((await db.scalars(select(Team).where(Team.task_id == task.id))).all())
        assert {team.name for team in saved} == {"9월 25일 등교조", "9월 26일 정리조"}

    await engine.dispose()


@pytest.mark.asyncio
async def test_scheduled_community_meeting_appears_only_on_manager_calendars():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="부장회의 캘린더 테스트",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        head = User(
            email="head@example.com",
            name="부장",
            password_hash="unused",
            role=Role.DEPARTMENT_HEAD,
            term_id=term.id,
        )
        executive = User(
            email="executive@example.com",
            name="회장단",
            password_hash="unused",
            role=Role.EXECUTIVE_BOARD,
            term_id=term.id,
        )
        member = User(
            email="ordinary-member@example.com",
            name="일반 임원",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([head, executive, member])
        await db.flush()
        db.add(
            CommunityPost(
                term_id=term.id,
                author_id=member.id,
                kind="IDEA",
                title="가을 캠페인 검토",
                content="회의에서 검토할 안건",
                agenda_at=datetime(2026, 9, 1, tzinfo=UTC),
                meeting_date=date(2026, 9, 3),
                meeting_time_slot="MORNING",
                meeting_time=time(8, 10),
            )
        )
        await db.commit()

        head_items = await calendar_items(date(2026, 9, 1), date(2026, 9, 30), head, db)
        executive_items = await calendar_items(
            date(2026, 9, 1), date(2026, 9, 30), executive, db
        )
        member_items = await calendar_items(date(2026, 9, 1), date(2026, 9, 30), member, db)

        assert any(
            item.source == "COMMUNITY_MEETING"
            and item.title == "부장회의 · 가을 캠페인 검토"
            and item.starts_at.hour == 8
            and item.starts_at.minute == 10
            for item in head_items
        )
        assert any(item.source == "COMMUNITY_MEETING" for item in executive_items)
        assert all(item.source != "COMMUNITY_MEETING" for item in member_items)

    await engine.dispose()


@pytest.mark.asyncio
async def test_team_formation_allows_only_declared_repeatable_members():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="반복 편성 테스트",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        teacher = User(
            email="repeat@example.com",
            name="반복 담당",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        member = User(
            email="repeat-member@example.com",
            name="매주 참여자",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([teacher, member])
        await db.flush()
        task = Task(
            term_id=term.id,
            title="주간 당번 편성",
            type=TaskType.TEAM_FORMATION,
            status=TaskStatus.TODO,
            created_by=teacher.id,
        )
        db.add(task)
        await db.flush()
        db.add(TaskAssignee(task_id=task.id, user_id=teacher.id))
        await db.commit()

        await submit_team_formation(
            task.id,
            TeamFormationIn(
                content="2주 반복 편성",
                repeatable_member_ids=[member.id],
                teams=[
                    TeamDraftIn(
                        name="1주차 1조",
                        leader_id=member.id,
                        member_ids=[member.id],
                        schedule_at=datetime(2026, 8, 17, 1, tzinfo=UTC),
                    ),
                    TeamDraftIn(
                        name="2주차 1조",
                        leader_id=member.id,
                        member_ids=[member.id],
                        schedule_at=datetime(2026, 8, 24, 1, tzinfo=UTC),
                    ),
                ],
            ),
            teacher,
            db,
        )
        saved_teams = list((await db.scalars(select(Team).where(Team.task_id == task.id))).all())
        assert len(saved_teams) == 2

    await engine.dispose()

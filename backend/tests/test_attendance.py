from datetime import date, time

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.attendance import list_attendance, mark_all_present, save_attendance
from app.api.events import create_event
from app.core.database import Base
from app.core.errors import AppError
from app.models.entities import (
    AttendanceStatus,
    AuditLog,
    Department,
    EventType,
    Role,
    Term,
    User,
)
from app.schemas import AttendanceIn, EventIn


@pytest.mark.asyncio
async def test_attendance_checklist_supports_batch_updates_and_member_privacy():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="출석 테스트 기수",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        department = Department(name="기획부")
        db.add_all([term, department])
        await db.flush()
        teacher = User(
            email="teacher@example.com",
            name="선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        first = User(
            email="first@example.com",
            name="첫째",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
            department_id=department.id,
            grade=1,
        )
        second = User(
            email="second@example.com",
            name="둘째",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
            department_id=department.id,
            grade=2,
        )
        outsider = User(
            email="outsider@example.com",
            name="외부인",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
            grade=3,
        )
        db.add_all([teacher, first, second, outsider])
        await db.flush()
        event = await create_event(
            EventIn(
                title="학생회 행사",
                type=EventType.EVENT,
                event_date=date.today(),
                starts_at=time(9),
                ends_at=time(17),
                department_id=department.id,
                manager_id=teacher.id,
                participant_ids=[first.id, second.id],
            ),
            teacher,
            db,
        )

        initial = await list_attendance(event.id, teacher, db)
        assert initial.can_edit is True
        assert initial.summary.total == 2
        assert initial.summary.pending == 2
        assert {item.user_name for item in initial.items} == {"첫째", "둘째"}

        saved = await save_attendance(
            event.id,
            [
                AttendanceIn(user_id=first.id, status=AttendanceStatus.PRESENT),
                AttendanceIn(user_id=second.id, status=AttendanceStatus.LATE, note="10분 지각"),
            ],
            teacher,
            db,
        )
        assert saved.summary.present == 1
        assert saved.summary.late == 1
        assert all(item.recorded_by_name == "선생님" for item in saved.items)
        assert await db.scalar(select(func.count()).select_from(AuditLog)) == 2

        member_view = await list_attendance(event.id, first, db)
        assert member_view.can_edit is False
        assert [item.user_id for item in member_view.items] == [first.id]

        with pytest.raises(AppError) as error:
            await save_attendance(
                event.id,
                [AttendanceIn(user_id=outsider.id, status=AttendanceStatus.PRESENT)],
                teacher,
                db,
            )
        assert error.value.code == "invalid_attendance_user"

        all_present = await mark_all_present(event.id, teacher, db)
        assert all_present.summary.present == 2
        assert all_present.summary.pending == 0

    await engine.dispose()

from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.admin import create_user, directory_users
from app.core.database import Base
from app.models.entities import Role, Term, User
from app.schemas import UserCreate


@pytest.mark.asyncio
async def test_directory_can_filter_active_users_by_grade():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="학년 테스트 기수",
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
        first_grade = User(
            email="first@example.com",
            name="1학년 학생",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
            grade=1,
        )
        second_grade = User(
            email="second@example.com",
            name="2학년 학생",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
            grade=2,
        )
        inactive = User(
            email="inactive@example.com",
            name="비활성 학생",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
            grade=1,
            is_active=False,
        )
        db.add_all([teacher, first_grade, second_grade, inactive])
        await db.commit()

        users = await directory_users(1, teacher, db)
        assert [user.id for user in users] == [first_grade.id]

        created = await create_user(
            UserCreate(
                email="NEW-MEMBER@example.com",
                name="신규 학생",
                password="12345678",
                role=Role.MEMBER,
                term_id=term.id,
                grade=3,
            ),
            teacher,
            db,
        )
        assert created.email == "new-member@example.com"
        assert created.grade == 3

    await engine.dispose()


def test_user_grade_must_be_middle_school_grade():
    with pytest.raises(ValidationError):
        UserCreate(
            email="member@example.com",
            name="학생",
            password="12345678",
            role=Role.MEMBER,
            term_id="78363c10-3f00-4d4d-ae31-2ee20c97d33f",
            grade=4,
        )

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.tutorial import start_tutorial, tutorial_status
from app.core.database import Base
from app.models.entities import (
    EventParticipant,
    NoticeRecipient,
    Role,
    Task,
    TaskAssignee,
    Term,
    TutorialWorkspace,
    User,
)


@pytest.mark.asyncio
async def test_tutorial_start_is_idempotent_and_assigns_real_records():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="튜토리얼 기수",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        member = User(
            email="new-member@example.com",
            name="새 임원",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add(member)
        await db.commit()

        first = await start_tutorial(member, db)
        second = await start_tutorial(member, db)
        current = await tutorial_status(member, db)

        assert first.started is True
        assert second.started is True
        assert current.total_count == 6
        assert await db.scalar(select(func.count()).select_from(TutorialWorkspace)) == 1
        assert await db.scalar(select(func.count()).select_from(Task)) == 3
        assert await db.scalar(select(func.count()).select_from(TaskAssignee)) == 3
        assert await db.scalar(select(func.count()).select_from(EventParticipant)) == 1
        assert await db.scalar(select(func.count()).select_from(NoticeRecipient)) == 1

    await engine.dispose()

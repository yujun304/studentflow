from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.notices import list_notices, update_notice
from app.core.database import Base
from app.models.entities import Notice, NoticeRecipient, NoticeType, Role, Term, User
from app.schemas import NoticeUpdate


@pytest.mark.asyncio
async def test_notice_editor_receives_recipients_and_can_update_notice():
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
        notice = Notice(
            term_id=term.id,
            title="준비물 안내",
            content="가위를 가져오세요.",
            type=NoticeType.GENERAL,
            author_id=teacher.id,
        )
        db.add(notice)
        await db.flush()
        db.add(NoticeRecipient(notice_id=notice.id, user_id=member.id))
        await db.commit()

        notices = await list_notices(teacher, db)
        assert notices[0].can_edit is True
        assert notices[0].recipient_ids == [member.id]

        updated = await update_notice(
            notice.id,
            NoticeUpdate(
                title="준비물 변경 안내",
                content="색종이를 가져오세요.",
                recipient_ids=[teacher.id, member.id],
            ),
            teacher,
            db,
        )
        assert updated.title == "준비물 변경 안내"
        assert set(updated.recipient_ids) == {teacher.id, member.id}

    await engine.dispose()

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.audit import list_audit_logs
from app.api.reminders import (
    create_memo,
    delete_memo,
    delete_saved_item,
    list_memos,
    list_saved_items,
    save_item,
)
from app.core.database import Base
from app.core.errors import AppError
from app.models.entities import AuditLog, Role, Task, TaskAssignee, TaskStatus, TaskType, Term, User
from app.schemas import QuickMemoIn, SavedItemIn


@pytest.mark.asyncio
async def test_quick_memos_are_trimmed_scoped_and_deletable():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="빠른 메모 테스트 기수",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        other_term = Term(
            name="이전 기수",
            starts_on=date(2025, 1, 1),
            ends_on=date(2025, 12, 31),
            is_current=False,
        )
        db.add_all([term, other_term])
        await db.flush()
        member = User(
            email="memo@example.com",
            name="메모 사용자",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        other = User(
            email="other-memo@example.com",
            name="다른 사용자",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([member, other])
        await db.commit()

        first = await create_memo(QuickMemoIn(content="  준비물 확인  "), member, db)
        await create_memo(QuickMemoIn(content="다른 사람 메모"), other, db)

        visible = await list_memos(member, db)
        assert [memo.content for memo in visible] == ["준비물 확인"]

        with pytest.raises(AppError) as error:
            await delete_memo(first.id, other, db)
        assert error.value.status == 404
        assert error.value.code == "memo_not_found"

        await delete_memo(first.id, member, db)
        assert await list_memos(member, db) == []

        with pytest.raises(AppError) as blank_error:
            await create_memo(QuickMemoIn(content="   "), member, db)
        assert blank_error.value.code == "memo_content_required"

    await engine.dispose()


@pytest.mark.asyncio
async def test_saved_tasks_are_scoped_and_audit_logs_include_actor_name():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="저장 항목 테스트 기수",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        teacher = User(
            email="saved-teacher@example.com",
            name="기록 선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        member = User(
            email="saved-member@example.com",
            name="저장 임원",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([teacher, member])
        await db.flush()
        task = Task(
            term_id=term.id,
            title="저장할 업무",
            type=TaskType.SIMPLE,
            status=TaskStatus.TODO,
            created_by=teacher.id,
        )
        db.add(task)
        await db.flush()
        db.add_all(
            [
                TaskAssignee(task_id=task.id, user_id=member.id),
                AuditLog(
                    actor_id=teacher.id,
                    action="ATTENDANCE_UPDATED",
                    entity_type="attendance",
                    entity_id=task.id,
                    detail=None,
                ),
            ]
        )
        await db.commit()

        saved = await save_item(
            SavedItemIn(target_type="task", target_id=task.id), member, db
        )
        duplicate = await save_item(
            SavedItemIn(target_type="task", target_id=task.id), member, db
        )
        assert duplicate.id == saved.id
        assert [item.id for item in await list_saved_items(member, db)] == [saved.id]

        logs = await list_audit_logs(None, 20, teacher, db)
        assert logs[0].actor_name == "기록 선생님"
        assert logs[0].action == "ATTENDANCE_UPDATED"

        await delete_saved_item(saved.id, member, db)
        assert await list_saved_items(member, db) == []

    await engine.dispose()

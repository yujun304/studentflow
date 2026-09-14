from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.comments import create_comment, delete_comment, list_comments
from app.core.database import Base
from app.core.errors import AppError
from app.models.entities import Role, Task, TaskAssignee, TaskStatus, TaskType, Term, User
from app.schemas import CommentIn


@pytest.mark.asyncio
async def test_task_comment_thread_checks_scope_and_supports_reply_and_soft_delete():
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
            name="댓글 테스트 기수",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        teacher = User(
            email="comment-teacher@example.com",
            name="담당 선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        member = User(
            email="comment-member@example.com",
            name="담당 임원",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        outsider = User(
            email="comment-outsider@example.com",
            name="다른 임원",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        db.add_all([teacher, member, outsider])
        await db.flush()
        task = Task(
            term_id=term.id,
            title="축제 준비",
            type=TaskType.SIMPLE,
            status=TaskStatus.TODO,
            created_by=teacher.id,
        )
        db.add(task)
        await db.flush()
        db.add(TaskAssignee(task_id=task.id, user_id=member.id))
        await db.commit()

        first = await create_comment(
            CommentIn(target_type="task", target_id=task.id, content=" 준비됐습니다. "),
            member,
            db,
        )
        assert first.content == "준비됐습니다."
        assert first.is_mine is True

        reply = await create_comment(
            CommentIn(
                target_type="task",
                target_id=task.id,
                parent_id=first.id,
                content="확인했습니다.",
            ),
            teacher,
            db,
        )
        thread = await list_comments("task", task.id, member, db)
        assert [item.id for item in thread] == [first.id, reply.id]
        assert thread[1].parent_id == first.id

        with pytest.raises(AppError) as denied:
            await list_comments("task", task.id, outsider, db)
        assert denied.value.status == 404

        await delete_comment(first.id, member, db)
        deleted_thread = await list_comments("task", task.id, member, db)
        assert deleted_thread[0].deleted is True
        assert deleted_thread[0].content == "삭제된 댓글입니다."

    await engine.dispose()

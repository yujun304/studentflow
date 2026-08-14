from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.notifications import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    send_notification,
)
from app.core.database import Base
from app.core.errors import AppError
from app.models.entities import Department, Role, Term, User
from app.schemas import NotificationSendIn


@pytest.mark.asyncio
async def test_notification_send_read_and_scope():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        term = Term(
            name="2026 test",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        department = Department(name="planning")
        other_department = Department(name="media")
        db.add_all([term, department, other_department])
        await db.flush()
        head = User(
            email="head@example.com",
            name="Head",
            password_hash="unused",
            role=Role.DEPARTMENT_HEAD,
            department_id=department.id,
            term_id=term.id,
        )
        member = User(
            email="member@example.com",
            name="Member",
            password_hash="unused",
            role=Role.MEMBER,
            department_id=department.id,
            term_id=term.id,
        )
        outsider = User(
            email="outsider@example.com",
            name="Outsider",
            password_hash="unused",
            role=Role.MEMBER,
            department_id=other_department.id,
            term_id=term.id,
        )
        db.add_all([head, member, outsider])
        await db.commit()

        created = await send_notification(
            NotificationSendIn(
                title="Schedule changed",
                content="Check the new time.",
                recipient_ids=[member.id],
            ),
            head,
            db,
        )
        assert len(created) == 1
        notifications = await list_notifications(member, db)
        assert notifications[0].title == "Schedule changed"
        assert notifications[0].read_at is None

        await mark_notification_read(notifications[0].id, member, db)
        assert (await list_notifications(member, db))[0].read_at is not None

        await mark_all_notifications_read(member, db)

        with pytest.raises(AppError) as error:
            await send_notification(
                NotificationSendIn(title="Invalid scope", recipient_ids=[outsider.id]),
                head,
                db,
            )
        assert error.value.status == 403
        assert error.value.code == "recipient_scope"

    await engine.dispose()

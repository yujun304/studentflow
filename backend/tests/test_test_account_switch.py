from datetime import date

import pytest
from fastapi import Request, Response
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.auth import switch_test_account
from app.api.auth import test_accounts as list_test_accounts
from app.core.config import settings
from app.core.database import Base
from app.core.errors import AppError
from app.models.entities import Role, Term, User


@pytest.mark.asyncio
async def test_development_account_switch_lists_same_term_and_issues_new_cookies(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
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
        other_term = Term(
            name="다른 기수",
            starts_on=date(2025, 1, 1),
            ends_on=date(2025, 12, 31),
            is_current=False,
        )
        db.add_all([term, other_term])
        await db.flush()
        actor = User(
            email="switch-actor@example.com",
            name="학생 임원",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=term.id,
        )
        teacher = User(
            email="switch-teacher@example.com",
            name="담당 선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=term.id,
        )
        other_user = User(
            email="other-term@example.com",
            name="이전 기수",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=other_term.id,
        )
        db.add_all([actor, teacher, other_user])
        await db.commit()

        accounts = await list_test_accounts(actor, db)
        assert {account.id for account in accounts} == {actor.id, teacher.id}

        response = Response()
        switched = await switch_test_account(
            teacher.id,
            Request({"type": "http", "headers": []}),
            response,
            actor,
            db,
        )
        assert switched.id == teacher.id
        cookies = "\n".join(response.headers.getlist("set-cookie"))
        assert "studentflow_access=" in cookies
        assert "studentflow_refresh=" in cookies

        with pytest.raises(AppError) as wrong_term:
            await switch_test_account(
                other_user.id,
                Request({"type": "http", "headers": []}),
                Response(),
                actor,
                db,
            )
        assert wrong_term.value.status == 404

    await engine.dispose()


@pytest.mark.asyncio
async def test_account_switch_is_hidden_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(AppError) as error:
        await list_test_accounts(None, None)
    assert error.value.status == 404

from types import SimpleNamespace
import uuid

from datetime import date

import pytest
from fastapi import Response
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.auth import login, login_email
from app.core.database import Base
from app.core.config import Settings
from app.core.security import decode_token, hash_password, verify_password, _encode
from app.models.entities import Role, Term, User
from app.schemas import LoginIn


def test_password_is_hashed_and_verifiable():
    hashed = hash_password("safe-password-123")
    assert hashed != "safe-password-123"
    assert verify_password("safe-password-123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_portfolio_login_ids_map_to_internal_emails():
    assert login_email("jo") == "jo@example.com"
    assert login_email(" JO ") == "jo@example.com"
    assert login_email("student") == "student@example.com"
    assert login_email(" STUDENT ") == "student@example.com"
    assert login_email("test") == "test@example.com"
    assert login_email(" TEST ") == "test@example.com"
    assert login_email("student1") == "student01@example.com"
    assert login_email(" STUDENT1 ") == "student01@example.com"
    assert login_email("teacher@example.com") == "teacher@example.com"


def test_student_number_maps_to_internal_email():
    assert login_email("30317") == "30317@studentflow.example.com"
    assert login_email(" 10125 ") == "10125@studentflow.example.com"
    assert login_email("1234") == "1234"


@pytest.mark.asyncio
async def test_user_can_login_with_korean_name_login_id():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        term = Term(
            name="이름 로그인 기수",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            is_current=True,
        )
        db.add(term)
        await db.flush()
        db.add(
            User(
                email="30317@studentflow.example.com",
                login_id="이유준",
                name="이유준",
                password_hash=hash_password("30317"),
                role=Role.EXECUTIVE_BOARD,
                term_id=term.id,
                grade=3,
            )
        )
        await db.commit()

        response = Response()
        signed_in = await login(LoginIn(email="이유준", password="30317"), response, db)
        assert signed_in.name == "이유준"
        assert "studentflow_access=" in "\n".join(response.headers.getlist("set-cookie"))

    await engine.dispose()


def test_multiple_frontend_origins_are_normalized():
    settings = Settings(
        _env_file=None,
        frontend_origin="http://localhost:8081/, https://portfolio.example.com/",
    )
    assert settings.allowed_frontend_origins == {
        "http://localhost:8081",
        "https://portfolio.example.com",
    }


def test_access_token_has_user_and_session_version():
    user = SimpleNamespace(id=uuid.uuid4(), session_version=3)
    from datetime import timedelta

    token = _encode(user, "access", timedelta(minutes=5))
    payload = decode_token(token, "access")
    assert payload["sub"] == str(user.id)
    assert payload["sv"] == 3

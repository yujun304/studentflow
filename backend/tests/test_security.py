from types import SimpleNamespace
import uuid

from app.api.auth import login_email
from app.core.config import Settings
from app.core.security import decode_token, hash_password, verify_password, _encode


def test_password_is_hashed_and_verifiable():
    hashed = hash_password("safe-password-123")
    assert hashed != "safe-password-123"
    assert verify_password("safe-password-123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_portfolio_login_ids_map_to_internal_emails():
    assert login_email("test") == "test@example.com"
    assert login_email(" TEST ") == "test@example.com"
    assert login_email("student1") == "student01@example.com"
    assert login_email(" STUDENT1 ") == "student01@example.com"
    assert login_email("teacher@example.com") == "teacher@example.com"


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

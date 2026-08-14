import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models.entities import RefreshSession, Role, User

password_hash = PasswordHash.recommended()
ACCESS_COOKIE = "studentflow_access"
REFRESH_COOKIE = "studentflow_refresh"
CSRF_COOKIE = "studentflow_csrf"


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return password_hash.verify(value, hashed)


def _encode(user: User, kind: str, expires: timedelta, token_id: str | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "typ": kind,
        "sv": user.session_version,
        "iat": now,
        "exp": now + expires,
        "jti": token_id or secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, kind: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("typ") != kind:
            raise ValueError
        return payload
    except (jwt.PyJWTError, ValueError) as exc:
        raise AppError(401, "invalid_token", "인증 정보가 유효하지 않습니다.") from exc


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def set_auth_cookies(response: Response, access: str, refresh: str, csrf: str) -> None:
    common = dict(secure=settings.cookie_secure, samesite="lax", domain=settings.cookie_domain)
    response.set_cookie(
        ACCESS_COOKIE, access, httponly=True, max_age=settings.access_token_minutes * 60, **common
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        httponly=True,
        max_age=settings.refresh_token_days * 86400,
        **common,
    )
    response.set_cookie(
        CSRF_COOKIE, csrf, httponly=False, max_age=settings.refresh_token_days * 86400, **common
    )


def clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, domain=settings.cookie_domain)


async def issue_tokens(db: AsyncSession, user: User) -> tuple[str, str, str]:
    jti = secrets.token_urlsafe(24)
    access = _encode(user, "access", timedelta(minutes=settings.access_token_minutes))
    refresh = _encode(user, "refresh", timedelta(days=settings.refresh_token_days), jti)
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=token_digest(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    await db.commit()
    return access, refresh, secrets.token_urlsafe(32)


async def current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise AppError(401, "not_authenticated", "로그인이 필요합니다.")
    payload = decode_token(token, "access")
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active or user.session_version != payload.get("sv"):
        raise AppError(401, "session_expired", "로그인 세션이 만료되었습니다.")
    return user


async def csrf_protect(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get("X-CSRF-Token")
    origin = request.headers.get("Origin")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise AppError(403, "csrf_failed", "요청 검증에 실패했습니다.")
    if origin and origin.rstrip("/") not in settings.allowed_frontend_origins:
        raise AppError(403, "origin_rejected", "허용되지 않은 요청 출처입니다.")


def require_roles(*roles: Role):
    async def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "forbidden", "이 작업을 수행할 권한이 없습니다.")
        return user

    return dependency


async def revoke_all_sessions(db: AsyncSession, user: User) -> None:
    user.session_version += 1
    await db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()


async def active_refresh_session(db: AsyncSession, token: str) -> RefreshSession | None:
    return await db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_digest(token),
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > datetime.now(UTC),
        )
    )

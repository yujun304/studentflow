import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import (
    REFRESH_COOKIE,
    active_refresh_session,
    clear_auth_cookies,
    csrf_protect,
    current_user,
    decode_token,
    issue_tokens,
    set_auth_cookies,
    token_digest,
    verify_password,
)
from app.models.entities import RefreshSession, User
from app.schemas import LoginIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
LOGIN_ALIASES = {
    "test": "test@example.com",
    "student1": "student01@example.com",
}


def login_email(value: str) -> str:
    identifier = value.strip().lower()
    return LOGIN_ALIASES.get(identifier, identifier)


@router.post("/login", response_model=UserOut, dependencies=[Depends(csrf_protect)])
async def login(data: LoginIn, response: Response, db: AsyncSession = Depends(get_db)) -> User:
    user = await db.scalar(select(User).where(User.email == login_email(data.email)))
    if not user or not verify_password(data.password, user.password_hash) or not user.is_active:
        raise AppError(401, "invalid_credentials", "아이디 또는 비밀번호가 올바르지 않습니다.")
    access, refresh, csrf = await issue_tokens(db, user)
    set_auth_cookies(response, access, refresh, csrf)
    return user


@router.post("/refresh", response_model=UserOut, dependencies=[Depends(csrf_protect)])
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise AppError(401, "missing_refresh", "다시 로그인해 주세요.")
    payload = decode_token(token, "refresh")
    session = await active_refresh_session(db, token)
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not session or not user or not user.is_active or user.session_version != payload.get("sv"):
        clear_auth_cookies(response)
        raise AppError(401, "invalid_refresh", "로그인 세션이 만료되었습니다.")
    session.revoked_at = datetime.now(UTC)
    access, new_refresh, csrf = await issue_tokens(db, user)
    set_auth_cookies(response, access, new_refresh, csrf)
    return user


@router.post("/logout", status_code=204, dependencies=[Depends(csrf_protect)])
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        session = await db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == token_digest(token))
        )
        if session:
            session.revoked_at = datetime.now(UTC)
            await db.commit()
    clear_auth_cookies(response)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/csrf")
async def csrf(request: Request, response: Response) -> dict[str, str]:
    import secrets
    from app.core.config import settings
    from app.core.security import CSRF_COOKIE

    value = request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(32)
    response.set_cookie(
        CSRF_COOKIE,
        value,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
    )
    return {"csrf_token": value}

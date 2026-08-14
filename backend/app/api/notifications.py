import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, current_user, require_roles
from app.models.entities import Notification, PushSubscription, Role, User
from app.schemas import (
    NotificationOut,
    NotificationSendIn,
    PushConfigOut,
    PushSubscriptionDeleteIn,
    PushSubscriptionIn,
)
from app.services.notifications import create_notifications, vapid_public_key

router = APIRouter(tags=["notifications"], dependencies=[Depends(csrf_protect)])
manager = require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    return list(
        (
            await db.scalars(
                select(Notification)
                .where(Notification.user_id == user.id)
                .order_by(Notification.created_at.desc())
                .limit(100)
            )
        ).all()
    )


@router.post("/notifications", response_model=list[NotificationOut], status_code=201)
async def send_notification(
    data: NotificationSendIn,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    requested = set(data.recipient_ids)
    statement = select(User.id).where(
        User.id.in_(requested), User.term_id == actor.term_id, User.is_active.is_(True)
    )
    if actor.role == Role.DEPARTMENT_HEAD:
        statement = statement.where(User.department_id == actor.department_id)
    allowed = set((await db.scalars(statement)).all())
    if requested != allowed:
        raise AppError(
            403, "recipient_scope", "현재 관리 범위의 사용자에게만 알림을 보낼 수 있습니다."
        )
    return await create_notifications(
        db,
        requested,
        notification_type="MANUAL",
        title=data.title,
        content=data.content,
        target_type=data.target_type,
        target_id=data.target_id,
    )


@router.post("/notifications/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    if not item:
        raise AppError(404, "notification_not_found", "알림을 찾을 수 없습니다.")
    if not item.read_at:
        item.read_at = datetime.now(UTC)
        await db.commit()


@router.post("/notifications/read-all", status_code=204)
async def mark_all_notifications_read(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    await db.commit()


@router.get("/push/config", response_model=PushConfigOut)
async def push_config(_: User = Depends(current_user)):
    public_key = vapid_public_key()
    return PushConfigOut(enabled=bool(public_key), public_key=public_key)


@router.post("/push-subscriptions", status_code=204)
async def subscribe(
    data: PushSubscriptionIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(default=None),
):
    if not vapid_public_key():
        raise AppError(503, "push_not_configured", "푸시 알림 키가 아직 설정되지 않았습니다.")
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == data.endpoint, PushSubscription.user_id != user.id
        )
    )
    item = await db.scalar(
        select(PushSubscription).where(
            PushSubscription.user_id == user.id, PushSubscription.endpoint == data.endpoint
        )
    )
    if item:
        item.p256dh = data.p256dh
        item.auth = data.auth
        item.user_agent = user_agent
    else:
        db.add(
            PushSubscription(
                user_id=user.id,
                endpoint=data.endpoint,
                p256dh=data.p256dh,
                auth=data.auth,
                user_agent=user_agent,
            )
        )
    await db.commit()
    return Response(status_code=204)


@router.delete("/push-subscriptions", status_code=204)
async def unsubscribe(
    data: PushSubscriptionDeleteIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.user_id == user.id, PushSubscription.endpoint == data.endpoint
        )
    )
    await db.commit()

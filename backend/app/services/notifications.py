import asyncio
import base64
import json
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid
from pywebpush import WebPushException, webpush_async
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entities import Notification, PushSubscription


def vapid_public_key() -> str | None:
    private_key = settings.vapid_private_key
    if not private_key:
        return None
    key_path = Path(private_key)
    vapid = (
        Vapid.from_file(private_key_file=str(key_path))
        if key_path.is_file()
        else Vapid.from_string(private_key=private_key)
    )
    raw = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


async def _send_one(subscription: PushSubscription, payload: str) -> tuple[uuid.UUID, bool]:
    try:
        await webpush_async(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=300,
            timeout=10,
        )
        return subscription.id, False
    except WebPushException as error:
        response = getattr(error, "response", None)
        status = getattr(response, "status", None) or getattr(response, "status_code", None)
        return subscription.id, status in {404, 410}
    except Exception:
        return subscription.id, False


async def send_push(
    db: AsyncSession,
    recipient_ids: set[uuid.UUID],
    *,
    title: str,
    content: str | None,
    url: str,
) -> None:
    if not settings.vapid_private_key or not recipient_ids:
        return
    subscriptions = list(
        (
            await db.scalars(
                select(PushSubscription).where(PushSubscription.user_id.in_(recipient_ids))
            )
        ).all()
    )
    if not subscriptions:
        return
    payload = json.dumps(
        {"title": title, "body": content or "새 알림이 도착했습니다.", "url": url},
        ensure_ascii=False,
    )
    results = await asyncio.gather(*(_send_one(item, payload) for item in subscriptions))
    expired = [subscription_id for subscription_id, should_delete in results if should_delete]
    if expired:
        await db.execute(delete(PushSubscription).where(PushSubscription.id.in_(expired)))
        await db.commit()


def notification_url(target_type: str | None, target_id: uuid.UUID | None) -> str:
    routes = {
        "task": "/tasks",
        "event": "/events",
        "notice": "/announcements",
        "submission": "/submissions",
    }
    base = routes.get(target_type, "/notifications")
    return (
        f"{base}/{target_id}" if target_id and target_type in {"task", "event", "notice"} else base
    )


async def create_notifications(
    db: AsyncSession,
    recipient_ids: set[uuid.UUID],
    *,
    notification_type: str,
    title: str,
    content: str | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
) -> list[Notification]:
    notifications = [
        Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            content=content,
            target_type=target_type,
            target_id=target_id,
        )
        for user_id in recipient_ids
    ]
    db.add_all(notifications)
    await db.commit()
    await send_push(
        db,
        recipient_ids,
        title=title,
        content=content,
        url=notification_url(target_type, target_id),
    )
    return notifications

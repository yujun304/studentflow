from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_roles
from app.models.entities import AuditLog, Role, User
from app.schemas import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    action: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    actor: User = Depends(require_roles(Role.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    statement = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        statement = statement.where(AuditLog.action == action)
    logs = list((await db.scalars(statement)).all())
    actor_ids = {log.actor_id for log in logs if log.actor_id}
    actors = {
        user.id: user.name
        for user in (
            await db.scalars(select(User).where(User.id.in_(actor_ids)))
        ).all()
    }
    return [
        AuditLogOut(
            id=log.id,
            actor_id=log.actor_id,
            actor_name=actors.get(log.actor_id, "시스템"),
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            detail=log.detail,
            created_at=log.created_at,
        )
        for log in logs
    ]
